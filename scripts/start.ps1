param(
  [string]$ImageName = "pm-mvp",
  [string]$ContainerName = "pm-mvp",
  [int]$Port = 8000
)

docker rm -f $ContainerName 2>$null | Out-Null
docker build -t $ImageName .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker run -d --name $ContainerName -p ${Port}:8000 --env-file .env $ImageName
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Running at http://127.0.0.1:$Port"
