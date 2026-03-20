FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    mininet \
    openvswitch-switch \
    openvswitch-testcontroller \
    python3 \
    python3-pip \
    iproute2 \
    iputils-ping \
    net-tools \
    iperf3 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir mininet

COPY topologies/ /topologies/
COPY scripts/ /scripts/

EXPOSE 6000

# Start OVS then the validation server on port 6000.
# The server listens for topology-validation requests from the
# api-gateway sandbox (Req-Func-Sw-9).
CMD ["/bin/bash", "-c", "service openvswitch-switch start && python3 /scripts/validation_server.py"]
