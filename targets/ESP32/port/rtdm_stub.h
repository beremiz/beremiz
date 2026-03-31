#pragma once

// Simula defines y tipos de rtdm.h para compilación
#define RTDM_UNUSED
typedef int rtdm_context_t;
typedef int rtdm_irq_t;
typedef int rtdm_mutex_t;

// Funciones vacías para compilación
static inline int rtdm_irq_request(rtdm_irq_t irq, void *handler, int flags, const char *name, void *dev) { return 0; }
static inline void rtdm_irq_free(rtdm_irq_t irq, void *dev) {}
static inline int rtdm_mutex_init(rtdm_mutex_t *mutex) { return 0; }
static inline void rtdm_mutex_lock(rtdm_mutex_t *mutex) {}
static inline void rtdm_mutex_unlock(rtdm_mutex_t *mutex) {}

