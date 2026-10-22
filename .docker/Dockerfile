FROM python:3.11-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git unzip less groff \
    && rm -rf /var/lib/apt/lists/*

# AWS CLI v2 (x86_64 o aarch64 según la máquina: Intel o Apple Silicon)
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o /tmp/awscliv2.zip \
    && unzip /tmp/awscliv2.zip -d /tmp \
    && /tmp/aws/install \
    && rm -rf /tmp/awscliv2.zip /tmp/aws

# Node.js 20 (para Serverless Framework)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g serverless@3

# Python tools
RUN pip install --no-cache-dir uv

WORKDIR /workspace

# Python dependencies del proyecto
COPY pyproject.toml .
RUN uv pip install --system -r pyproject.toml --extra dev

CMD ["bash"]
