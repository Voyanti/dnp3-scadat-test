FROM python:3.8-alpine

# Install system dependencies
RUN set -x && \
    apk add --no-cache \
        openrc \
        cmake \
        build-base \
        git

# Clone the dnp3-python repository
RUN git clone --recurse-submodules https://github.com/your-repo/dnp3-python.git /opt/dnp3-python

# Set up Python environment
RUN python3 -m ensurepip && \
    pip3 install --upgrade pip setuptools wheel && \
    cd /opt/dnp3-python && \
    python3 setup.py bdist_wheel --plat-name=manylinux1_x86_64 && \
    pip3 install dist/dnp3_python-*.whl


    ENV WORK_DIR=workdir \
    HASSIO_DATA_PATH=/data
  
  RUN mkdir -p ${WORK_DIR}
  WORKDIR /${WORK_DIR}
  COPY requirements.txt .
  
  # install python libraries
  RUN pip3 install -r requirements.txt
  
  # Copy code
  COPY outstation.py ./
  COPY run.sh  ./
  
  
  # Run
  RUN chmod a+x run.sh
  CMD [ "sh", "./run.sh" ]