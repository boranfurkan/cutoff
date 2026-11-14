"""User store on SQLite."""
from sqlalchemy import Column, Integer, String, create_engine, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    plan = Column(String, default="free")


def make_engine():
    engine = create_engine("sqlite://")
    Base.metadata.bind = engine
    Base.metadata.create_all()
    return engine


def add_users(engine, names):
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add_all([User(name=n) for n in names])
    session.commit()
    return session


def count(engine):
    return engine.execute("SELECT count(*) FROM users").scalar()


def names(engine):
    with engine.connect() as conn:
        return [row["name"] for row in conn.execute(select([User.name]).order_by(User.name))]


def get(session, user_id):
    return session.query(User).get(user_id)


def upgrade(engine, name):
    engine.execute(User.__table__.update().where(User.name == name).values(plan="pro"))
