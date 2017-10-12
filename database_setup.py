import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Index
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

# User

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))

# Category

class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, unique=True)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
        }

# Item

class Item(Base):
    __tablename__ = 'item'

    __table_args__ = (
        Index(
            'ix_unique_item_category',  # Index name
            'name', 'category_id',  # Columns which are part of the index
            unique=True),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(2000))
    created_date = Column(DateTime, server_default=func.now())
    modified_date = Column(DateTime, onupdate=func.now())
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'description': self.description,
            'id': self.id,
        }


#engine = create_engine('sqlite:///itemcatalog.db')

engine = create_engine('postgresql://vagrant:vagrant@localhost:5432/catalog')

Base.metadata.create_all(engine)
