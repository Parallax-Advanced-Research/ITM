FROM ubuntu:latest

# the list of python libs we're installing is just there to get them into the
# local cache so we don't have to download them again in every job in the CI
# pipeline. The docker image doesn't need to be updated if we add a new
# library; all requirements will be installed normally later.
# Similarly, it's fine if some of these fail due to conflicts. We just get
# locally cached versions of as many as we can.
RUN \
useradd -m -d /home/itm -s /bin/bash itm && \
apt-get update && \
apt-get install -y git sudo iputils-ping python3.10 python3.10-venv python3-pip && \
echo 'itm ALL=(root) NOPASSWD: /usr/bin/apt, /usr/bin/apt-get' >> /etc/sudoers && \
ln -s /usr/bin/python3.10 /usr/bin/python && \
LIBS='alembic==1.12.0 anyio==3.7.0 blinker==1.6.3 Bootstrap-Flask==2.3.2 build certifi>=14.05.14 cl4py==1.8.1 click==8.1.3 click==8.1.7 colorama==0.4.6 connexion>=2.6.0 connexion[swagger-ui]<=2.14.2 connexion[swagger-ui]>=2.6.0 fastapi fastapi==0.98.0 Flask==2.1.1 Flask==3.0.0 Flask-Migrate==4.0.5 Flask-SQLAlchemy==3.1.1 Flask-WTF==1.2.1 greenlet==3.0.0 h11==0.14.0 httptools==0.5.0 idna==3.4 itsdangerous==2.1.2 Jinja2==3.1.2 joblib==1.2.0 Mako==1.2.4 MarkupSafe==2.1.3 matplotlib motor mypy numpy numpy==1.25.0 pandas pandas==2.0.2 plotly pyAgrum==1.9.0 pyarrow pydantic pydantic==1.10.9 pyflakes pylint pytest python_dateutil>=2.5.3 python_dateutil==2.6.0 python_dateutil>=2.6.0 python-dateutil==2.8.2 python-dotenv==1.0.0 pytz==2023.3 PyYAML PyYAML==6.0 PyYAML==6.0.1 requests requests==2.31.0 scikit-learn scikit-learn==1.2.2 scipy scipy==1.11.0 setuptools>=21.0.0 six>=1.10 six==1.16.0 skrebate==0.6 sniffio==1.3.0 SQLAlchemy==2.0.22 starlette==0.27.0 streamlit==1.31.0 swagger-ui-bundle>=0.0.2 swagger-ui-bundle==0.0.9 threadpoolctl==3.1.0 tomli typing_extensions==4.6.3 typing_extensions==4.8.0 tzdata==2023.3 urllib3>=1.15.1 uvicorn uvicorn==0.22.0 watchfiles==0.19.0 websockets==11.0.3 Werkzeug==3.0.0 WTForms==3.1.0' && \
for lib in $LIBS; do sudo -u itm python -m pip install "$lib"; done

WORKDIR /home/itm
USER itm
