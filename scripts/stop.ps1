param(
  [string]$ContainerName = "pm-mvp"
)

docker stop $ContainerName 2>$null | Out-Null
docker rm $ContainerName 2>$null | Out-Null
Write-Host "Stopped $ContainerName"
