FROM solarkennedy/wine-x11-novnc-docker
ENV WINEPREFIX /root/prefix64
ENV WINEARCH win64
COPY [../xmglobal5setup.exe, "/root/prefix64/drive_c/Program Files/XM Global MT5"]
COPY ./supervisord.conf /etc/supervisor/conf.d/supervisord.conf
EXPOSE 8080
