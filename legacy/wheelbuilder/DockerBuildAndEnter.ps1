$ErrorActionPreference = "Stop"
$ImageName = "raspbian-trixie-wheel-shell"

# Resolve repo root (two levels up from this script)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Resolve-Path (Join-Path $ScriptDir "..\..\..\")

# Enable qemu binfmt for ARM
docker run --privileged --rm tonistiigi/binfmt --install arm | Out-Null

# Buildx builder (idempotent)
try { docker buildx inspect raspbian | Out-Null }
catch { docker buildx create --name raspbian --use | Out-Null }
docker buildx inspect --bootstrap | Out-Null

# Build image (Dockerfile is in this folder)
docker buildx build `
  --platform linux/arm/v6 `
  -t $ImageName `
  --load `
  $ScriptDir

# Enter interactive shell with repo root mounted
docker run --rm -it `
  --platform linux/arm/v6 `
  -e QEMU_CPU=arm1176 `
  -v "${RepoRoot}:/work" `
  $ImageName
