FROM continuumio/miniconda3:latest AS miniconda-stage

FROM debian:latest

RUN apt-get update && apt-get install -y \
    wget \
    git \
    gcc \
    build-essential \
    vim \
    curl \
    unzip \
    inetutils-ping \
    tmux \
    watch \
    && apt-get clean

COPY --from=miniconda-stage /opt/conda /opt/conda
ENV PATH="/opt/conda/bin:${PATH}"

WORKDIR /root

RUN git clone https://github.com/Bald0Wang/DeepSeek-Oracle.git

RUN curl https://raw.githubusercontent.com/creationix/nvm/master/install.sh | bash \
    && /bin/bash -c "source ~/.bashrc && nvm install 18.12" \
    && /bin/bash -c "source ~/.bashrc && npm install pnpm -g" \
    && /bin/bash -c "source ~/.bashrc && pnpm add -S iztro express --prefix /root/DeepSeek-Oracle/" \


SHELL ["/bin/bash", "-c"]

RUN conda init bash

RUN conda create -n deepseek-oracle python=3.9 -y \
    && echo "conda activate deepseek-oracle" >> ~/.bashrc

RUN /bin/bash -c "source ~/.bashrc && conda activate deepseek-oracle && pip install -r /root/DeepSeek-Oracle/requirements.txt"

CMD ["/bin/bash"]
