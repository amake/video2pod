FROM public.ecr.aws/lambda/python:3.11

RUN yum -y install xz tar make \
    && rm -rf /var/cache/yum \
    && curl -o ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/old-releases/ffmpeg-4.4.1-arm64-static.tar.xz \
    && tar -xf ffmpeg.tar.xz \
    && ln -s $PWD/ffmpeg-*-arm64-static/ffmpeg /usr/local/bin/ffmpeg \
    && ln -s $PWD/ffmpeg-*-arm64-static/ffprobe /usr/local/bin/ffprobe \
    && rm -rf ffmpeg.tar.xz

COPY requirements.txt ${LAMBDA_TASK_ROOT}

RUN pip3 install -r requirements.txt

COPY Makefile config.ini *.py ${LAMBDA_TASK_ROOT}

ENV XDG_CACHE_HOME=/tmp/.cache

CMD ["lambda.run"]
