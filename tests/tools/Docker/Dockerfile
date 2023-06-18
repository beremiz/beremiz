#
# Dockerfile for Beremiz
# This container is used to run tests for Beremiz
#
FROM ubuntu:jammy  
                                        
ENV TERM xterm-256color
    
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

ARG UNAME=testing
ENV UNAME ${UNAME}
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID $UNAME
RUN useradd -m -u $UID -g $GID -s /bin/bash $UNAME

RUN set -xe \
    && apt-get update \
    && apt-get install locales \
    && locale-gen en_US.UTF-8 \
    && update-locale LANG=en_US.UTF-8

RUN set -xe \
    && TZ="America/Paris" \
       DEBIAN_FRONTEND="noninteractive" \
       apt-get install -y --no-install-recommends \
               `# to run sikuli` \
               wget \
               openjdk-11-jre \
               libtesseract4 \
               \
               `# to run X based tests` \
               fluxbox \
               wmctrl xdotool xvfb \
               x11vnc xterm xnest \
               materia-gtk-theme \
               \
               `# to build tested apps` \
               build-essential automake flex bison mercurial \
               libgtk-3-dev libgl1-mesa-dev libglu1-mesa-dev \
               libpython3.10-dev libssl-dev \
               python3.10 virtualenv cmake git


# force bigger font and flat theme for GTK in order to make OCR more reliable
RUN mkdir -p /etc/gtk-3.0
RUN env echo -e '[Settings]\ngtk-font-name=FreeSans,12\ngtk-theme-name=Materia\n' > /etc/gtk-3.0/settings.ini

# link obtained from https://raiman.github.io/SikuliX1/downloads.html
RUN set -xe && \
    wget -qP /usr/local/bin \
        https://launchpad.net/sikuli/sikulix/2.0.5/+download/sikulixide-2.0.5.jar && \
    echo 0795f1e0866ee5a7a84e4c89793ea78c /usr/local/bin/sikulixide-2.0.5.jar | md5sum -c && \
    ( echo '#!/bin/sh' && \
      echo "exec java -jar /usr/local/bin/sikulixide-*.jar \"\$@\"" \
    ) | install /dev/stdin /usr/local/bin/sikulix


# easy to remember 'do_tests' alias to invoke main makefile
RUN env echo -e '#!/bin/bash\nmake -f /home/testing/src/beremiz/tests/Makefile $*' > /usr/local/bin/do_tests
RUN chmod +x /usr/local/bin/do_tests

USER $UNAME

RUN mkdir /home/$UNAME/build /home/$UNAME/src /home/$UNAME/test

RUN virtualenv ~/beremizenv

# wxPython build req
RUN ~/beremizenv/bin/pip install gattrdict

RUN ~/beremizenv/bin/pip install wxpython

RUN ~/beremizenv/bin/pip install \
        pytest pytest-timeout ddt \
        sslpsk posix_spawn \
        matplotlib lxml \
        zeroconf \
        pycountry \
        Pyro5 msgpack autobahn click

RUN ~/beremizenv/bin/pip install \
        git+https://github.com/FreeOpcUa/opcua-asyncio.git@98a64897a2d171653353de2f36d33085aef65e82 \
        git+https://github.com/beremiz/nevow-py3.git@nevow-0.14.5.dev1

RUN set -xe && \
    cd  /home/$UNAME && mkdir tessdata && \
    wget -q https://github.com/tesseract-ocr/tessdata/archive/refs/tags/4.1.0.tar.gz \
         -O tessdata.tar.gz && \
    echo 89e25c7c40a59be7195422a01f57fcb2 tessdata.tar.gz | md5sum -c && \
    tar --strip-components=1 -C tessdata -x -v -z -f tessdata.tar.gz && \
    rm tessdata.tar.gz

ENV TESSDATAPATH /home/$UNAME/tessdata

# Points to python binary that test will use
ENV BEREMIZPYTHONPATH /home/$UNAME/beremizenv/bin/python

