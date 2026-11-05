%global nvidia_version 610.43.03
%global kernel_version %(uname -r)
%global debug_package %{nil}
# GPU firmware ELF files must not be modified by the host strip tool.
%global __strip /bin/true

Name: gpu-unlock
Version: 2.0.0
Release: 1%{?dist}
Summary: RTX 3090 BF16 unlock before the NVIDIA driver loads
License: GPL-2.0-only
ExclusiveArch: x86_64
Source0: gpu-unlock-%{version}.tar.xz
Source1: https://download.nvidia.com/XFree86/NVIDIA-kernel-module-source/NVIDIA-kernel-module-source-%{nvidia_version}.tar.xz
Source2: https://download.nvidia.com/XFree86/Linux-x86_64/%{nvidia_version}/NVIDIA-Linux-x86_64-%{nvidia_version}-no-compat32.run
# NVIDIA inputs stay out of the source RPM (it becomes a .nosrc.rpm).
NoSource: 1
NoSource: 2
BuildRequires: make
BuildRequires: gcc
BuildRequires: python3
BuildRequires: zstd
BuildRequires: kernel-devel-uname-r = %{kernel_version}

%description
Kernel module that unlocks RTX 3090 BF16 throughput before the unmodified
NVIDIA driver binds, opted in on the kernel command line.

%package kmod
Summary: Precompiled GPU unlock module for %{kernel_version}
Requires: kernel-uname-r = %{kernel_version}
Requires: gpu-unlock-firmware = %{version}-%{release}
Requires(posttrans): kmod, dracut
Requires(postun): kmod, dracut
Conflicts: gpu-unlock-dkms

%description kmod
Precompiled gpu_unlock kernel module for %{kernel_version}, loaded ahead of
nvidia. No compiler or DKMS is required on the target host. It does nothing
unless gpu_unlock.targets= is on the kernel command line.

%package firmware
Summary: Locally generated pinned NVIDIA firmware for GPU unlock
License: LicenseRef-NVIDIA AND GPL-2.0-only
BuildArch: noarch

%description firmware
Firmware assets generated locally from verified upstream inputs.

%prep
sha256sum -c - <<EOF
7e118923c7a23edc36114d63273a46e3e04e9af98695a42203e7ac2dfe9fc1dc  %{SOURCE1}
e084451db730a6df29d3d74f655749c4d236e3c945f7d94b5205e84318fe2f90  %{SOURCE2}
EOF
%autosetup
test "$(cat VERSION)" = "%{version}"

%build
%make_build -C kernel/gpu_unlock KDIR=/lib/modules/%{kernel_version}/build
%make_build INPUTS=%{_sourcedir} ASSETS="$PWD/assets" firmware

%install
make DESTDIR=%{buildroot} ASSETS="$PWD/assets" \
    install-firmware
install -Dm644 kernel/gpu_unlock/gpu_unlock.ko \
    %{buildroot}%{_prefix}/lib/modules/%{kernel_version}/extra/gpu-unlock/gpu_unlock.ko
install -Dm644 README.md %{buildroot}%{_docdir}/gpu-unlock/README.md
mkdir -p %{buildroot}%{_prefix}/lib/dracut/dracut.conf.d
cat > %{buildroot}%{_prefix}/lib/dracut/dracut.conf.d/gpu-unlock.conf <<'EOF'
# Only include the precompiled module for its matching kernel.
if [[ "${kernel:-$(uname -r)}" == "%{kernel_version}" ]]; then
    force_drivers+=" gpu_unlock "
fi
EOF

%files kmod
%license licenses/GPL-2.0.txt licenses/CMP40HX-MIT.txt licenses/NVIDIA-MIT.txt
%doc %{_docdir}/gpu-unlock
%{_prefix}/lib/modules/%{kernel_version}/extra/gpu-unlock
%{_prefix}/lib/dracut/dracut.conf.d/gpu-unlock.conf

%files firmware
%license %{_defaultlicensedir}/gpu-unlock-firmware
%{_prefix}/lib/firmware/gpu-unlock

%posttrans kmod
set -e
depmod -a %{kernel_version}
dracut --force --kver %{kernel_version}

%postun kmod
set -e
if [ "$1" -eq 0 ]; then
    depmod -a %{kernel_version}
    dracut --force --kver %{kernel_version}
fi

%changelog
* Tue Oct 27 2026 Zagitta <zetlon+github@gmail.com> - 2.0.0-1
- Add Turing and Ada Lovelace support.

* Mon Sep 28 2026 Zagitta <zetlon+github@gmail.com> - 1.1.0-1
- Initial release.
