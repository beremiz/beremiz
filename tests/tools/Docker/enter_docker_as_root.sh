#!/bin/bash

CONTAINER=beremiz_playwright_current

docker start $CONTAINER
docker exec -i -t -u root $CONTAINER bash
docker stop $CONTAINER
