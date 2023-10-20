import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "7aJ#JxP4Td2GRR@V@9P4"
    # We'll use sqlite for now, but we'll want to use postgresql in production
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL") or "sqlite:///"
    ) + os.path.join(basedir, "casebases.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
