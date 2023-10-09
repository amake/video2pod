# video2pod

[Well There's Your Problem](https://wtyppod.podbean.com) is a podcast about
engineering disasters and systemic failures, from a leftist perspective, with
jokes.

While it is a podcast, it also has slides. The "full" experience is available in
the form of
[videos](https://www.youtube.com/@welltheresyourproblempodca1465/featured),
which are hard to get into your podcast player.

This project squares the circle as follows:

1. Download the videos
2. Extract the slides
3. Extract the audio
4. Add the slides to the audio in the form of chapter art
5. Clone the podcast feed such that it points to the audio with chapter art

## Requirements

- Python 3
- ffmpeg 4

Optional (for deploying on AWS):

- awscli
- Docker

## Setup

1. Clone this repo
2. Copy `config.ini.example` to `config.ini` and fill it out. The `deployment`
   section is only required if you plan to deploy this to AWS Lambda.
3. Run `make archive` to download the videos
4. Run `make all` to produce the chapterized audio files. Look in the `dist`
   directory.

If you want to use the audio files directly then you're done. To publish as a
podcast, you will need to prepare an AWS S3 bucket, an AWS ECR repo, and an AWS
Lambda function and set the appropriate values in `config.ini`.

5. Run `make deploy` to copy the distfiles to S3
6. Run `make build` to build a Docker image capable of updating the feed
7. Run `make push` to push the Docker image to ECR and update the Lambda
   function to use it

The Lambda function will need a lot of RAM, storage, and execution time. Tuning
is left as an exercise for the reader.

## Where can I listen to it?

You can't, because I'm not in the business of hosting podcasts. If you are
affiliated with Well There's Your Problem and would like access for the purposes
of investigating whether these tools could be useful in publishing an official
chapterized feed, then please contact me.
