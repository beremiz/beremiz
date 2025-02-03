/*
 * Beremiz C++ runtime
 *
 * This file implements Beremiz C++ programmable runtime for Zephyr
 *
 * Copyright 2025 Beremiz SAS
 * 
 * See COPYING for licensing details
 */

#include <stdio.h>

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>

// eRPC includes
#include "erpc_basic_codec.hpp"
#include "erpc_serial_transport.hpp"
#include "erpc_tcp_transport.hpp"
#include "erpc_simple_server.hpp"

// eRPC generated includes
#include "erpc_PLCObject_server.hpp"

#include "PLCObject.hpp"


int main(void)
{
	printf("Beremiz programmable runtime for Zephyr\n");
	return 0;
}
