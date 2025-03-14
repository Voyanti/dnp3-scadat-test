FROM python:3.10-alpine

# Install build dependencies
RUN apk add --no-cache \
    git \
    build-base \
    cmake \
    python3-dev \
    gcc \
    g++ \
    make \
    linux-headers \
    ca-certificates \
    musl-dev \
    libstdc++    # Add this to keep the runtime library

# Create a working directory
WORKDIR /build

# Clone the repository with submodules
RUN git clone --recurse-submodules https://github.com/VOLTTRON/dnp3-python.git .

# Add include for stdint.h
RUN sed -i '1i#include <cstdint>' deps/pybind11/include/pybind11/attr.h

# Set environment variables for the build
ENV CFLAGS="-I/usr/include"
ENV CXXFLAGS="-I/usr/include"

# Install build requirements and dependencies
RUN python3 -m pip install --no-cache-dir cmake setuptools wheel \
        paho-mqtt cattrs

# Build and install the package
RUN python3 setup.py install

# Clean up build dependencies but keep runtime dependencies
RUN apk del git build-base cmake python3-dev gcc g++ make linux-headers

# Create a non-root user
ENV WORK_DIR=workdir \
    HASSIO_DATA_PATH=/data
  
RUN mkdir -p ${WORK_DIR}
WORKDIR /${WORK_DIR}
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# install python libraries
RUN pip3 install dnp3-python
# dnp3-python==0.2.3b2
# Copy code
COPY src/  ./src/
COPY run.sh  ./


# Run
RUN chmod a+x run.sh
CMD [ "sh", "./run.sh" ]