FROM eclipse-temurin:24-jre-noble

RUN groupadd -g 322 lavalink && \
    useradd -u 322 -g lavalink -m -d /opt/Lavalink lavalink

WORKDIR /opt/Lavalink

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

RUN wget -O Lavalink.jar https://github.com/lavalink-devs/Lavalink/releases/download/4.0.8/Lavalink.jar

COPY --chown=lavalink:lavalink application.yml .

RUN mkdir -p plugins && chown -R lavalink:lavalink /opt/Lavalink

USER lavalink

EXPOSE 2333

ENTRYPOINT ["java", "-Djdk.tls.client.protocols=TLSv1.1,TLSv1.2", "-Xmx1G", "-jar", "Lavalink.jar"]
