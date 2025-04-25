FROM python

# STAGE 0 : COPY SOURCE CODE
COPY Bot /opt/discord-music-bot


# STAGE 2 : CREATE REQUIREMENTS FILE AND INSTALL DEPENDENCIES
RUN pip install -r /opt/discord-music-bot/requirements.txt

# STAGE 3 : WORKDIR
WORKDIR /opt/discord-music-bot

COPY entrypoint.sh /opt/discord-music-bot/entrypoint.sh
RUN chmod +x /opt/discord-music-bot/entrypoint.sh

VOLUME ["/opt/discord-music-bot"]

# STAGE 4 : RUN
CMD ["sh", "/opt/discord-music-bot/entrypoint.sh"]
