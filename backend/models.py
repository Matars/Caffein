"""
SQLAlchemy models for PostgreSQL database
"""
from sqlalchemy import Column, Integer, String, Numeric, TIMESTAMP, DATE, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    type = Column(String(50), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class FireDetection(Base):
    """NASA FIRMS satellite fire detection model"""
    __tablename__ = 'fire_detections'

    id = Column(Integer, primary_key=True)
    latitude = Column(Numeric(10, 6), nullable=False)
    longitude = Column(Numeric(11, 6), nullable=False)
    acq_date = Column(DATE, nullable=False)
    acq_time = Column(String(4))
    confidence = Column(String(10))
    frp = Column(Numeric(10, 2))  # Fire Radiative Power (MW)
    brightness = Column(Numeric(10, 2))
    bright_t31 = Column(Numeric(10, 2))
    instrument = Column(String(20))  # MODIS or VIIRS
    satellite = Column(String(50))
    version = Column(String(20))
    daynight = Column(String(1))  # D or N
    type = Column(String(10))
    scan = Column(Numeric(10, 2))
    track = Column(Numeric(10, 2))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'latitude': float(self.latitude) if self.latitude is not None else None,
            'longitude': float(self.longitude) if self.longitude is not None else None,
            'acq_date': self.acq_date.isoformat() if self.acq_date else None,
            'acq_time': self.acq_time,
            'confidence': self.confidence,
            'frp': float(self.frp) if self.frp is not None else None,
            'brightness': float(self.brightness) if self.brightness is not None else None,
            'bright_t31': float(self.bright_t31) if self.bright_t31 is not None else None,
            'instrument': self.instrument,
            'satellite': self.satellite,
            'version': self.version,
            'daynight': self.daynight,
            'type': self.type,
            'scan': float(self.scan) if self.scan is not None else None,
            'track': float(self.track) if self.track is not None else None
        }
