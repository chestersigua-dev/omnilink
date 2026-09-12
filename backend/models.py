import datetime
import json
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Table
)
from sqlalchemy.orm import relationship
from backend.database import Base

# Many-to-Many association table for Groups and Devices
device_group_members = Table(
    "device_group_members",
    Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    Column("device_id", Integer, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    full_name = Column(String(128), default="")
    bio = Column(Text, default="")
    avatar_url = Column(String(256), default="")
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # Cascading relationships
    devices = relationship("Device", back_populates="owner", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="owner", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_uid = Column(String(64), index=True, nullable=False)
    name = Column(String(128), nullable=False)
    brand = Column(String(32), nullable=False) # xiaomi, tapo, samsung, lg, tcl
    model = Column(String(64), default="")
    device_type = Column(String(32), default="generic") # bulb, plug, tv, ac, purifier
    ip_address = Column(String(64), default="127.0.0.1")
    mac_address = Column(String(32), default="")
    port = Column(Integer, default=0)
    protocol = Column(String(32), default="")
    
    # State tracking
    is_online = Column(Boolean, default=True)
    power_state = Column(Boolean, default=False)
    level = Column(Integer, default=50) # Brightness / Volume / Temp (0-100)
    state_json = Column(Text, default="{}") # Extra protocol payload / metadata

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    owner = relationship("User", back_populates="devices")
    groups = relationship("Group", secondary=device_group_members, back_populates="devices")

    def get_state_dict(self):
        try:
            return json.loads(self.state_json) if self.state_json else {}
        except Exception:
            return {}

    def set_state_dict(self, state: dict):
        self.state_json = json.dumps(state)

    def to_dict(self):
        return {
            "id": self.id,
            "device_uid": self.device_uid,
            "name": self.name,
            "brand": self.brand,
            "model": self.model,
            "device_type": self.device_type,
            "ip_address": self.ip_address,
            "mac_address": self.mac_address,
            "port": self.port,
            "protocol": self.protocol,
            "is_online": self.is_online,
            "power_state": self.power_state,
            "level": self.level,
            "state": self.get_state_dict(),
            "user_id": self.user_id,
            "group_ids": [g.id for g in self.groups] if self.groups else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, default="")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    owner = relationship("User", back_populates="groups")
    devices = relationship("Device", secondary=device_group_members, back_populates="groups")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "device_count": len(self.devices) if self.devices else 0,
            "devices": [d.to_dict() for d in self.devices] if self.devices else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
