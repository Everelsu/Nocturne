FROM eclipse-temurin:24-jre-noble

RUN groupadd -g 322 lavalink && \
    useradd -u 322 -g lavalink -m -d /opt/Lavalink lavalink

WORKDIR /opt/Lavalink

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

RUN wget -O Lavalink.jar https://github.com/lavalink-devs/Lavalink/releases/download/4.0.8/Lavalink.jar

COPY --chown=lavalink:lavalink application.yml .

RUN mkdir -p plugins && \
    wget --tries=5 --retry-connrefused --waitretry=10 --timeout=60 \
        -O plugins/youtube-plugin-1.18.0.jar \
        https://github.com/lavalink-devs/youtube-source/releases/download/1.18.0/youtube-plugin-1.18.0.jar && \
    wget --tries=5 --retry-connrefused --waitretry=10 --timeout=60 \
        -O plugins/lavasrc-plugin-4.8.1.jar \
        https://github.com/topi314/LavaSrc/releases/download/4.8.1/lavasrc-plugin-4.8.1.jar && \
    chown -R lavalink:lavalink /opt/Lavalink

USER lavalink

EXPOSE 2333

ENTRYPOINT ["java", "-Djdk.tls.client.protocols=TLSv1.1,TLSv1.2", "-Xmx1G", "-jar", "Lavalink.jar"]
