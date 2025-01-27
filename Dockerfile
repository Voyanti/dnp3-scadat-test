FROM python:3.10-alpine

# Install system dependencies
RUN set -x && \
    apk add --no-cache \
        build-base \
        git \
        boost-dev \ 
        openssl-dev \
        libffi-dev \
        musl-dev


RUN pip3 install cmake==3.25.0 pybind11

# Clone the dnp3-python repository
RUN git clone --recurse-submodules https://github.com/VOLTTRON/dnp3-python.git /opt/dnp3-python

# Set up Python environment
RUN cd /opt/dnp3-python && \
    python3 setup.py bdist_wheel --plat-name=linux_armv7l


ENV WORK_DIR=workdir \
    HASSIO_DATA_PATH=/data
  
RUN mkdir -p ${WORK_DIR}
WORKDIR /${WORK_DIR}
# COPY requirements.txt .
# RUN pip3 install -r requirements.txt

# install python libraries
# RUN pip3 install dnp3-python
# dnp3-python==0.2.3b2
# Copy code
COPY outstation.py ./
COPY run.sh  ./


# Run
RUN chmod a+x run.sh
CMD [ "sh", "./run.sh" ]