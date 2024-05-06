#!/usr/bin/env bash

functionsFile=$1
gcfConfig=$2

region=""
projectID=""

while IFS= read -r line; do
	lineArr=($line)
	if [[ ${lineArr[0]} == "region" ]]; then
		region=${lineArr[1]}
	elif [[ ${lineArr[0]} == "projectID" ]]; then
		projectID=${lineArr[1]}
	fi
done < "$gcfConfig"

while IFS= read -r line; do
	if [[ $line == *"def "* ]]; then
		lineArr=($line)
		fnSign=${lineArr[1]}
		
		IFS='(' read -ra FUN <<< "$fnSign"
		fnName=${FUN[0]}

		gcloud functions deploy $fnName \
			--runtime python310 \
			--trigger-http \
			--entry-point $fnName \
			--source . \
			--region $region \
			--project $projectID
	fi
done < "$functionsFile"
