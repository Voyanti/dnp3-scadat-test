# Stage 1: The "builder" stage
FROM python:3.10-alpine AS builder

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
    libstdc++

WORKDIR /build

# Clone the repository
RUN git clone --recurse-submodules https://github.com/VOLTTRON/dnp3-python.git .

# Patch fix
RUN sed -i '1i#include <cstdint>' deps/pybind11/include/pybind11/attr.h

# Set environment variables for the build
ENV CFLAGS="-I/usr/include"
ENV CXXFLAGS="-I/usr/include"

# Install build-time python packages
RUN python3 -m pip install --no-cache-dir 'cmake<=3.31.6' setuptools wheel

# Build the Python wheel file
RUN python3 setup.py bdist_wheel

# ---

# Stage 2: The final, lean image
FROM python:3.10-alpine

# Install only RUNTIME dependencies
RUN apk add --no-cache libstdc++

# Copy the built wheel from the "builder" stage
COPY --from=builder /build/dist/*.whl /tmp/

# Install the wheel
RUN pip install /tmp/*.whl && rm /tmp/*.whl
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a work directory and non-root user (optional but good practice)
WORKDIR /app

# Copy your application code
COPY src/  ./src/
COPY run.sh  ./

# Run
RUN chmod a+x run.sh
CMD [ "sh", "./run.sh" ]