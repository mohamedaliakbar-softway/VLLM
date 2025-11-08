from database import engine, Base
from models import Project, Short

# Create all tables
Base.metadata.create_all(bind=engine)
print("Database tables created successfully!")
