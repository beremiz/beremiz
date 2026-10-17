#!/bin/bash

# Build IEC61131 language test with a Linux PLC-SDK made of an aarch64 sysroot,
# and run it under qemu, a minimal loader standing in for the runtime.
#
# Needs clang, lld, qemu-user and Debian's arm64 cross libc and libgcc,
# installed or unpacked with dpkg-deb -x in $CROSS_ROOT.

set -e

CROSS=/usr/aarch64-linux-gnu
GCC_DIR=$(ls -d $CROSS_ROOT/usr/lib/gcc-cross/aarch64-linux-gnu/* | sort -V | tail -1)
GCC_INSTALL_DIR=sysroot/usr/lib/gcc/aarch64-beremiz-linux/$(basename $GCC_DIR)

# Debian cross packages are a prefix, not a root filesystem. Lay them out as
# Yocto's populate_sdk sysroot is, gcc files in a vendor specific directory
rm -rf sysroot
mkdir -p sysroot/usr
cp -a $CROSS_ROOT$CROSS/include sysroot/usr/include
cp -a $CROSS_ROOT$CROSS/lib sysroot/usr/lib
ln -s usr/lib sysroot/lib
mkdir -p $GCC_INSTALL_DIR
find $GCC_DIR -maxdepth 1 -type f -exec cp {} $GCC_INSTALL_DIR \;
sed -i "s#$CROSS/lib/#/usr/lib/#g" $(grep -l "^GROUP\|^INPUT" sysroot/usr/lib/*.so)

# Distro's clang plays the toolchain shared by SDKs
export BEREMIZ_APPDATA=$(readlink -f appdata)
LLVM_DIR=$(dirname $(dirname $(readlink -f $(command -v clang))))
mkdir -p $BEREMIZ_APPDATA/toolchains
ln -sfn $LLVM_DIR $BEREMIZ_APPDATA/toolchains/test-llvm

rm -rf sdk build
$BEREMIZPYTHONPATH $BEREMIZPATH/targets/Linux/make_plc_sdk.py \
    --sysroot sysroot --target aarch64-linux-gnu --name test-aarch64 \
    --toolchain test-llvm sdk

$BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_cli.py --sdkpath sdk \
    --project-home $BEREMIZPATH/tests/projects/iec61131_lang_test \
    --buildpath build build

$LLVM_DIR/bin/clang --target=aarch64-linux-gnu --sysroot=sysroot \
    --gcc-install-dir=$GCC_INSTALL_DIR -fuse-ld=lld \
    -o plc_split_loader $BEREMIZPATH/tests/tools/plc_split_loader.c \
    -Wl,--no-as-needed -lm

qemu-aarch64 -L sysroot ./plc_split_loader \
    build/iec61131_lang_test.so build/iec61131_lang_test_logic.so "ALL TESTS OK"
