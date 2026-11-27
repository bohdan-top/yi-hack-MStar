ARG BASE_IMAGE=sha256:fb5b23e71c65e126bb2dd9c8bdcf612d54ffff59767893cfad303a633446443f
FROM ${BASE_IMAGE}
COPY debs /opt/fw001/debs
COPY hashes.txt /opt/fw001/hashes.txt
COPY linaro.tar.xz /opt/fw001/linaro.tar.xz
RUN cd /opt/fw001 && sha256sum -c hashes.txt \
    && apt-get --yes --no-download --no-install-recommends -o Dir::Cache::archives=/opt/fw001/debs install /opt/fw001/debs/*.deb \
    && test -z "$(dpkg --audit)" \
    && mkdir -p /opt/yi \
    && tar -xJf /opt/fw001/linaro.tar.xz -C /opt/yi \
    && mv /opt/yi/gcc-linaro-arm-linux-gnueabihf-4.8-2014.04_linux /opt/yi/arm-linux-gnueabihf-4.8.3-201404 \
    && dpkg-query -W > /opt/fw001/installed-packages.tsv \
    && rm -rf /opt/fw001/debs /opt/fw001/linaro.tar.xz /var/lib/apt/lists/* /var/cache/apt/archives/*
