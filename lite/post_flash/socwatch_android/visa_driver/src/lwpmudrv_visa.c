/*COPYRIGHT**
    Copyright (C) 2005-2013 Intel Corporation.  All Rights Reserved.

    This file is part of VISA Development Kit

    VISA Development Kit is free software; you can redistribute it
    and/or modify it under the terms of the GNU General Public License
    version 2 as published by the Free Software Foundation.

    VISA Development Kit is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with VISA Development Kit; if not, write to the Free Software
    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

    As a special exception, you may use this file as part of a free software
    library without restriction.  Specifically, if other files instantiate
    templates or use macros or inline functions from this file, or you compile
    this file and link it with other files to produce an executable, this
    file does not by itself cause the resulting executable to be covered by
    the GNU General Public License.  This exception does not however
    invalidate any other reasons why the executable file might be covered by
    the GNU General Public License.
**COPYRIGHT*/

#include "lwpmudrv_defines.h"


#include <linux/version.h>
#include <linux/module.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/fs.h>
#include <linux/errno.h>
#include <linux/types.h>
#include <asm/page.h>
#include <linux/cdev.h>
#include <linux/proc_fs.h>
#include <linux/fcntl.h>
#include <linux/device.h>
#include <asm/uaccess.h>
#include <linux/sched.h>
#include <linux/syscalls.h>
#include <asm/unistd.h>
#include <linux/compat.h>

#include "lwpmudrv_types.h"
#include "rise_errors.h"
#include "lwpmudrv_ecb.h"
#include "lwpmudrv_ioctl.h"
#include "lwpmudrv_struct.h"
#include "inc/ecb_iterators.h"

//#include "pci.h"

//#include "cpumon.h"
#include "lwpmudrv.h"
#include "utility.h"
#include "control.h"
#include "valleyview_sochap.h"

//#include "linuxos.h"
//#include "sys_info.h"

MODULE_AUTHOR("Copyright(c) 2007-2011 Intel Corporation");
MODULE_VERSION(SEP_NAME"_"SEP_VERSION_STR);
MODULE_LICENSE("Dual BSD/GPL");

typedef struct LWPMU_DEV_NODE_S  LWPMU_DEV_NODE;
typedef        LWPMU_DEV_NODE   *LWPMU_DEV;

struct LWPMU_DEV_NODE_S {
  long              buffer;
  struct semaphore  sem;
  struct cdev       cdev;
};

#define LWPMU_DEV_buffer(dev)      (dev)->buffer
#define LWPMU_DEV_sem(dev)         (dev)->sem
#define LWPMU_DEV_cdev(dev)        (dev)->cdev

/* Global variables of the driver */
SEP_VERSION_NODE        drv_version;
U64                    *read_unc_ctr_info     = NULL;
//VOID                  **PMU_register_data     = NULL;
#if defined(DRV_IA32) || defined(DRV_EM64T)
#endif
DISPATCH                dispatch_visa         = NULL;
EVENT_CONFIG            global_ec             = NULL;
volatile S32            abnormal_terminate    = 0;
LWPMU_DEV               visa_control         = NULL;

LWPMU_DEVICE            device_visa          = NULL;
CPU_STATE               pcb                  = NULL;
size_t                  pcb_size             = 0;

#if defined(DRV_USE_UNLOCKED_IOCTL)
static   struct mutex   ioctl_lock;
#endif

#define  PMU_DEVICES            2   // pmu, mod
#define  OTHER_PMU_DEVICES      1   // mod

static dev_t     lwpmu_DevNum;  /* the major and minor parts for SEP3 base */

#if defined (DRV_ANDROID) || defined (DRV_CHROMEOS)
static struct class         *pmu_class   = NULL;
#endif

#if defined (DRV_ANDROID)
#define DRV_DEVICE_DELIMITER "_"
#elif defined (DRV_CHROMEOS)
#define DRV_DEVICE_DELIMITER "/"
#endif

//U64               *pmu_state           = NULL;


#if !defined(DRV_USE_UNLOCKED_IOCTL)
#define MUTEX_INIT(lock)
#define MUTEX_LOCK(lock)
#define MUTEX_UNLOCK(lock)
#else
#define MUTEX_INIT(lock)     mutex_init(&(lock));
#define MUTEX_LOCK(lock)     mutex_lock(&(lock))
#define MUTEX_UNLOCK(lock)   mutex_unlock(&(lock))
#endif


/* ------------------------------------------------------------------------- */
/*!
 * @fn  static OS_STATUS lwpmudrv_Initialize_State(void)
 *
 * @param none
 *
 * @return OS_STATUS
 *
 * @brief  Allocates the memory needed at load time.  Initializes all the
 * @brief  necessary state variables with the default values.
 *
 * <I>Special Notes</I>
 */
static OS_STATUS
lwpmudrv_Initialize_State (
    VOID
)
{
    /*
     *  Machine Initializations
     *  Abstract this information away into a separate entry point
     *
     *  Question:  Should we allow for the use of Hot-cpu
     *    add/subtract functionality while the driver is executing?
     */

    GLOBAL_STATE_num_cpus(driver_state)          = num_online_cpus();
    GLOBAL_STATE_active_cpus(driver_state)       = num_online_cpus();
    GLOBAL_STATE_cpu_count(driver_state)         = 0;
    GLOBAL_STATE_dpc_count(driver_state)         = 0;
    GLOBAL_STATE_num_em_groups(driver_state)     = 0;
    GLOBAL_STATE_current_phase(driver_state)     = DRV_STATE_UNINITIALIZED;

    SEP_PRINT_DEBUG("lwpmudrv_Initialize_State: num_cpus=%d, active_cpus=%d\n",
                    GLOBAL_STATE_num_cpus(driver_state),
                    GLOBAL_STATE_active_cpus(driver_state));

    return OS_SUCCESS;
}


/* ------------------------------------------------------------------------- */
/*!
 * @fn       VOID UTILITY_Configure_CPU
 *
 * @brief    Reads the CPU information from the hardware
 *
 * @param    param   dispatch_id -  The id of the dispatch table.
 *
 * @return   Pointer to the correct dispatch table for the CPU architecture
 *
 * <I>Special Notes:</I>
 *              <NONE>
 */
extern  DISPATCH
UTILITY_Configure_CPU (
    U32 dispatch_id
)
{
    DISPATCH     dispatch = NULL;
    switch (dispatch_id) {
#if defined(DRV_IA32) || defined(DRV_EM64T)
        case 700:
            SEP_PRINT("Set up the Valleyview SA dispatch table\n");
            dispatch = &valleyview_visa_dispatch;
            break;
#endif

        default:
            dispatch = NULL;
            SEP_PRINT_ERROR("Architecture not supported (dispatch_id=%d)\n", dispatch_id);
            break;
    }

    return dispatch;
}


/* ------------------------------------------------------------------------- */
/*!
 * @fn       VOID UTILITY_Configure_CPU
 *
 * @brief    Reads the CPU information from the hardware
 *
 * @param    param   dispatch_id -  The id of the dispatch table.
 *
 * @return   Pointer to the correct dispatch table for the CPU architecture
 *
 * <I>Special Notes:</I>
 *              <NONE>
 */
extern  VOID
LWPMUDRV_VISA_Read_Data (
    PVOID data_buffer
)
{
    if (dispatch_visa && dispatch_visa->read_current_data) {
        smp_call_function_single(0, dispatch_visa->read_current_data, data_buffer, 1);
    }
    SEP_PRINT_DEBUG("LWPMUDRV_VISA_Read_Data called\n");
    return ;
}
EXPORT_SYMBOL(LWPMUDRV_VISA_Read_Data);

/*********************************************************************
 *  Internal Driver functions
 *     Should be called only from the lwpmudrv_DeviceControl routine
 *********************************************************************/

/* ------------------------------------------------------------------------- */
/*!
 * @fn  static OS_STATUS lwpmudrv_Version(IOCTL_ARGS arg)
 *
 * @param arg - pointer to the IOCTL_ARGS structure
 *
 * @return OS_STATUS
 *
 * @brief  Local function that handles the LWPMU_IOCTL_VERSION call.
 * @brief  Returns the version number of the kernel mode sampling.
 *
 * <I>Special Notes</I>
 */
static OS_STATUS
lwpmudrv_Version (
    IOCTL_ARGS   arg
)
{
    OS_STATUS status;

    // Check if enough space is provided for collecting the data
    if ((arg->r_len != sizeof(U32))  || (arg->r_buf == NULL)) {
        return OS_FAULT;
    }

    status = put_user(SEP_VERSION_NODE_sep_version(&drv_version), (U32 *)arg->r_buf);

    return status;
}

/* ------------------------------------------------------------------------- */
/*!
 * @fn  static VOID lwpmudrv_Clean_Up(DRV_BOOL)
 *
 * @param  DRV_BOOL finish - Flag to call finish
 *
 * @return VOID
 *
 * @brief  Cleans up the memory allocation.
 *
 * <I>Special Notes</I>
 */
static VOID
lwpmudrv_Clean_Up (
    DRV_BOOL finish
)
{
    U32  i = 0;
/*
    if (PMU_register_data) {
        for (i = 0; i < GLOBAL_STATE_num_em_groups(driver_state); i++) {
            CONTROL_Free_Memory(PMU_register_data[i]);
        }
    }
*/
    if (dispatch_visa && dispatch_visa->clean_up) {
        dispatch_visa->clean_up((VOID*) &i);
    }
#if defined(DRV_IA32) || defined(DRV_EM64T)
    if (device_visa) {
        EVENT_CONFIG  ec;
        if (LWPMU_DEVICE_PMU_register_data(device_visa)) {
            ec =  LWPMU_DEVICE_ec(device_visa);
            for (i = 0; i < EVENT_CONFIG_num_groups_unc(ec); i++) {
                CONTROL_Free_Memory(LWPMU_DEVICE_PMU_register_data(device_visa)[i]);
            }
            //LWPMU_DEVICE_PMU_register_data(device_visa) = CONTROL_Free_Memory(LWPMU_DEVICE_PMU_register_data(device_visa));
        }
        LWPMU_DEVICE_pcfg(device_visa) = CONTROL_Free_Memory(LWPMU_DEVICE_pcfg(device_visa));
        LWPMU_DEVICE_ec(device_visa)   = CONTROL_Free_Memory(LWPMU_DEVICE_ec(device_visa));
        device_visa = CONTROL_Free_Memory(device_visa);
    }
#endif

    //PMU_register_data       = CONTROL_Free_Memory(PMU_register_data);
    //global_ec               = CONTROL_Free_Memory(global_ec);

    //if (finish) {
    //    dispatch_visa->fini(NULL);
    //}
    //pmu_state               = CONTROL_Free_Memory(pmu_state);
    pcb                     = CONTROL_Free_Memory(pcb);
    pcb_size                = 0;
    GLOBAL_STATE_num_em_groups(driver_state)   = 0;
    GLOBAL_STATE_num_descriptors(driver_state) = 0;

    return;
}



/* ------------------------------------------------------------------------- */
/*!
 * @fn  static OS_STATUS lwpmudrv_Initialize_Visa(PVOID in_buf, U32 in_buf_len)
 *
 * @param  in_buf       - pointer to the input buffer
 * @param  in_buf_len   - size of the input buffer
 *
 * @return OS_STATUS
 *
 * @brief  Local function that handles the LWPMU_IOCTL_INIT call.
 * @brief  Sets up the interrupt handler.
 * @brief  Set up the output buffers/files needed to make the driver
 * @brief  operational.
 *
 * <I>Special Notes</I>
 */
static OS_STATUS
lwpmudrv_Initialize_Visa (
    PVOID         in_buf,
    U32           in_buf_len
)
{
    DRV_CONFIG  pcfg_unc;

    SEP_PRINT_DEBUG("Entered lwpmudrv_Initialize_UNC\n");
    cmpxchg(&GLOBAL_STATE_current_phase(driver_state),
                             DRV_STATE_UNINITIALIZED,
                             DRV_STATE_IDLE);

    if (GLOBAL_STATE_current_phase(driver_state) != DRV_STATE_IDLE) {
        SEP_PRINT_ERROR("OS_IN_PROGRESS error!\n");
        return OS_IN_PROGRESS;
    }
    /*
     *   Program State Initializations:
     *   Foreach device, copy over pcfg_unc and configure dispatch table
     */
    if (in_buf == NULL) {
        SEP_PRINT_ERROR("in_buff ERROR!\n");
        return OS_FAULT;
    }
    if (in_buf_len != sizeof(DRV_CONFIG_NODE)) {
        SEP_PRINT_ERROR("Got in_buf_len=%d, expecting size=%d\n", in_buf_len, (int)sizeof(DRV_CONFIG_NODE));
        return OS_FAULT;
    }

    device_visa = CONTROL_Allocate_Memory(sizeof(LWPMU_DEVICE_NODE));
    if (!device_visa) {
        SEP_PRINT_ERROR("Memory allocation failure for device_visa!\n");
        return OS_NO_MEM;
    }
    pcb_size = GLOBAL_STATE_num_cpus(driver_state)*sizeof(CPU_STATE_NODE);
    pcb      = CONTROL_Allocate_Memory(pcb_size);
    if (!pcb) {
        SEP_PRINT_ERROR("Memory allocation failure for pcb!\n");
        return OS_NO_MEM;
    }

    // allocate memory
    LWPMU_DEVICE_pcfg(device_visa) = CONTROL_Allocate_Memory(sizeof(DRV_CONFIG_NODE));
    if (!LWPMU_DEVICE_pcfg(device_visa)) {
        SEP_PRINT_ERROR("Memory allocation failure for LWPMU_DEVICE_pcfg(device_visa)!\n");
        return OS_NO_MEM;
    }
    // copy over pcfg_unc
    if (copy_from_user(LWPMU_DEVICE_pcfg(device_visa), in_buf, in_buf_len)) {
        SEP_PRINT_ERROR("Failed to copy from user");
        return OS_FAULT;
    }
    // configure dispatch from dispatch_id
    pcfg_unc = (DRV_CONFIG)LWPMU_DEVICE_pcfg(device_visa);

    LWPMU_DEVICE_dispatch(device_visa) = UTILITY_Configure_CPU(DRV_CONFIG_dispatch_id(pcfg_unc));
    if (LWPMU_DEVICE_dispatch(device_visa) == NULL) {
        SEP_PRINT_ERROR("Unable to configure CPU");
        return OS_FAULT;
    }

    LWPMU_DEVICE_em_groups_count(device_visa) = 0;
    LWPMU_DEVICE_cur_group(device_visa)       = 0;
    SEP_PRINT("LWP Config : unc dispatch id   = %d\n", DRV_CONFIG_dispatch_id(pcfg_unc));

    return OS_SUCCESS;
}


/* ------------------------------------------------------------------------- */
/*!
 * @fn  static OS_STATUS visa_Terminate(void)
 *
 * @param  none
 *
 * @return OS_STATUS
 *
 * @brief  Local function that handles the LWPMUDRV_IOCTL_TERMINATE call.
 * @brief  Cleans up the interrupt handler and resets the PMU state.
 *
 * <I>Special Notes</I>
 */
static OS_STATUS
visa_Terminate (
    VOID
)
{
    U32            previous_state;
    //SEP_PRINT("VISA terminate called\n");

    if (GLOBAL_STATE_current_phase(driver_state) == DRV_STATE_UNINITIALIZED) {
        return OS_SUCCESS;
    }

    previous_state = cmpxchg(&GLOBAL_STATE_current_phase(driver_state),
                             DRV_STATE_STOPPED,
                             DRV_STATE_UNINITIALIZED);
    if (previous_state != DRV_STATE_STOPPED) {
        SEP_PRINT_ERROR("visa_Terminate: Sampling is in progress, cannot terminate.\n");
        return OS_IN_PROGRESS;
    }

    GLOBAL_STATE_current_phase(driver_state) = DRV_STATE_UNINITIALIZED;
    //SEP_PRINT("VISA calling cleanup\n");
    lwpmudrv_Clean_Up(TRUE);
    //SEP_PRINT("VISA cleanup called\n");

    return OS_SUCCESS;
}







/* ------------------------------------------------------------------------- */
/*!
 * @fn static OS_STATUS lwpmudrv_Trigger_Read(void)
 *
 * @param - none
 *
 * @return - OS_STATUS
 *
 * @brief Read the Counter Data.
 *
 * <I>Special Notes</I>
 */
static OS_STATUS
lwpmudrv_Trigger_Read (
    VOID
)
{
#if defined(DRV_IA32) || defined(DRV_EM64T)

    dispatch_visa = LWPMU_DEVICE_dispatch(device_visa);
    if (dispatch_visa && dispatch_visa->trigger_read ) {
        dispatch_visa->trigger_read();
    }

#endif

    return OS_SUCCESS;
}


/* ------------------------------------------------------------------------- */
/*!
 * @fn static OS_STATUS lwpmudrv_Init_PMU(void)
 *
 * @param - none
 *
 * @return - OS_STATUS
 *
 * @brief Initialize the PMU and the driver state in preparation for data collection.
 *
 * <I>Special Notes</I>
 */
static OS_STATUS
lwpmudrv_Init_PMU (
    VOID
)
{
#if defined(DRV_IA32) || defined(DRV_EM64T)
    U32        i = 0;
#endif

    if (GLOBAL_STATE_current_phase(driver_state) != DRV_STATE_IDLE) {
        return OS_IN_PROGRESS;
    }
    dispatch_visa = LWPMU_DEVICE_dispatch(device_visa);
    if (dispatch_visa && dispatch_visa->write) {
        dispatch_visa->write((VOID *)&i);
    }
    SEP_PRINT_DEBUG("lwpmudrv_Init_PMU: IOCTL_Init_PMU - finished initial Write\n");

    return OS_SUCCESS;
}




/* ------------------------------------------------------------------------- */
/*!
 * @fn static OS_STATUS lwpmudrv_Set_EM_Config_UNC(IOCTL_ARGS arg)
 *
 * @param arg - pointer to the IOCTL_ARGS structure
 *
 * @return OS_STATUS
 *
 * @brief  Set the number of em groups in the global state node.
 * @brief  Also, copy the EVENT_CONFIG struct that has been passed in,
 * @brief  into a global location for now.
 *
 * <I>Special Notes</I>
 */
static OS_STATUS
lwpmudrv_Set_EM_Config_Visa (
    IOCTL_ARGS arg
)
{
    EVENT_CONFIG    ec;
    SEP_PRINT_DEBUG("enter lwpmudrv_Set_EM_Config_UNC\n");
    if (GLOBAL_STATE_current_phase(driver_state) != DRV_STATE_IDLE) {
        return OS_IN_PROGRESS;
    }

    // allocate memory
    LWPMU_DEVICE_ec(device_visa) = CONTROL_Allocate_Memory(sizeof(EVENT_CONFIG_NODE));
    if (!LWPMU_DEVICE_ec(device_visa)) {
        SEP_PRINT_ERROR("Memory allocation failure for LWPMU_DEVICE_ec(device_visa)!\n");
        return OS_NO_MEM;
    }
    if (copy_from_user(LWPMU_DEVICE_ec(device_visa), arg->w_buf, arg->w_len)) {
        return OS_FAULT;
    }
    // configure num_groups from ec of the specific device
    ec = (EVENT_CONFIG)LWPMU_DEVICE_ec(device_visa);
    LWPMU_DEVICE_PMU_register_data(device_visa) = CONTROL_Allocate_Memory(EVENT_CONFIG_num_groups_unc(ec) *
                                                                                   sizeof(VOID *));
    if (!LWPMU_DEVICE_PMU_register_data(device_visa)) {
        SEP_PRINT_ERROR("Memory allocation failure for LWPMU_DEVICE_PMU_register_data(device_visa)!\n");
        return OS_NO_MEM;
    }
    LWPMU_DEVICE_em_groups_count(device_visa) = 0;

    return OS_SUCCESS;
}

/* ------------------------------------------------------------------------- */
/*!
 * @fn static OS_STATUS lwpmudrv_Configure_events_UNC(IOCTL_ARGS arg)
 *
 * @param arg - pointer to the IOCTL_ARGS structure
 *
 * @return OS_STATUS
 *
 * @brief  Make a copy of the uncore registers that need to be programmed
 * @brief  for the next event set used for event multiplexing
 *
 * <I>Special Notes</I>
 */
static OS_STATUS
visa_Configure_Events_VISA (
    IOCTL_ARGS arg
)
{
    VOID              **PMU_register_data_unc;
    S32               em_groups_count_unc;
    ECB               ecb;
    EVENT_CONFIG      ec_unc;
    DRV_CONFIG        pcfg_unc;
    U32               group_id = 0;
    ECB               in_ecb   = NULL;

    if (GLOBAL_STATE_current_phase(driver_state) != DRV_STATE_IDLE) {
        return OS_IN_PROGRESS;
    }

    em_groups_count_unc = LWPMU_DEVICE_em_groups_count(device_visa);
    PMU_register_data_unc = LWPMU_DEVICE_PMU_register_data(device_visa);
    ec_unc                = LWPMU_DEVICE_ec(device_visa);
    pcfg_unc              = LWPMU_DEVICE_pcfg(device_visa);

    if (em_groups_count_unc >= (S32)EVENT_CONFIG_num_groups_unc(ec_unc)) {
        SEP_PRINT_DEBUG("Number of Uncore EM groups exceeded the initial configuration.");
        return OS_SUCCESS;
    }
     if (arg->w_buf == NULL || arg->w_len == 0) {
        return OS_FAULT;
    }
    //       size is in w_len, data is pointed to by w_buf
    //
    in_ecb                          = (ECB)arg->w_buf;
    group_id                        = ECB_group_id(in_ecb);
    PMU_register_data_unc[group_id] = CONTROL_Allocate_Memory(arg->w_len);
    if (!PMU_register_data_unc[group_id]) {
        SEP_PRINT_ERROR("ECB memory allocation failed\n");
        return OS_NO_MEM;
    }

    //
    // Make a copy of the data for global use.
    //
    if (copy_from_user(PMU_register_data_unc[group_id], arg->w_buf, arg->w_len)) {
        SEP_PRINT_ERROR("ECB copy failed\n");
        return OS_NO_MEM;
    }

    // at this point, we know the number of uncore events for this device,
    // so allocate the results buffer per thread for uncore only for SEP event based uncore counting
    if (em_groups_count_unc == 0) {
        ecb = PMU_register_data_unc[0];
        LWPMU_DEVICE_num_events(device_visa) = ECB_num_events(ecb);
    }
    LWPMU_DEVICE_em_groups_count(device_visa) = group_id + 1;

    return OS_SUCCESS;
}





/* ------------------------------------------------------------------------- */
/*!
 * @fn static OS_STATUS visa_Start(void)
 *
 * @param none
 *
 * @return OS_STATUS
 *
 * @brief  Local function that handles the LWPMU_IOCTL_START call.
 * @brief  Set up the OS hooks for process/thread/load notifications.
 * @brief  Write the initial set of MSRs.
 *
 * <I>Special Notes</I>
 */
static OS_STATUS
visa_Start (
    VOID
)
{
    OS_STATUS  status       = OS_SUCCESS;
    U32        previous_state;
#if defined(DRV_IA32) || defined(DRV_EM64T)
    U32        i = 0;
#endif

    /*
     * To Do: Check for state == STATE_IDLE and only then enable sampling
     */
    previous_state = cmpxchg(&GLOBAL_STATE_current_phase(driver_state),
                             DRV_STATE_IDLE,
                             DRV_STATE_RUNNING);
    if (previous_state != DRV_STATE_IDLE) {
        SEP_PRINT_ERROR("visa_Start: Unable to start sampling - State is %d\n",
                        GLOBAL_STATE_current_phase(driver_state));
        return OS_IN_PROGRESS;
    }

    if (dispatch_visa && dispatch_visa->restart) {
        dispatch_visa->restart((VOID*)&i);
    }

    return status;
}

/*
 * @fn lwpmudrv_Prepare_Stop();
 *
 * @param        NONE
 * @return       OS_STATUS
 *
 * @brief  Local function that handles the LWPMUDRV_IOCTL_STOP call.
 * @brief  Cleans up the interrupt handler.
 */
static OS_STATUS
visa_Prepare_Stop (
    VOID
)
{
    U32 i = 0;
    U32 current_state       = GLOBAL_STATE_current_phase(driver_state);

    SEP_PRINT_DEBUG("visa_Prepare_Stop: About to stop sampling\n");
    GLOBAL_STATE_current_phase(driver_state) = DRV_STATE_PREPARE_STOP;

    if (current_state == DRV_STATE_UNINITIALIZED) {
        return OS_SUCCESS;
    }

    if (dispatch_visa && dispatch_visa->freeze) {
        dispatch_visa->freeze((VOID*) &i);
    }

    return OS_SUCCESS;
}

/*
 * @fn visa_Finish_Stop();
 *
 * @param  NONE
 * @return OS_STATUS
 *
 * @brief  Local function that handles the LWPMUDRV_IOCTL_STOP call.
 * @brief  Cleans up the interrupt handler.
 */
static OS_STATUS
visa_Finish_Stop (
    VOID
)
{
    //U32        current_state = GLOBAL_STATE_current_phase(driver_state);
    OS_STATUS  status        = OS_SUCCESS;

    GLOBAL_STATE_current_phase(driver_state) = DRV_STATE_STOPPED;

    return status;
}


/* ------------------------------------------------------------------------- */
/*!
 * @fn static OS_STATUS lwpmudrv_Read_VISA_Counts(void out_buf, U32 out_buf_len)
 *
 * @param - out_buf       - output buffer
 *          out_buf_len   - output buffer length
 *
 * @return - OS_STATUS
 *
 * @brief    Read the Counter Data.
 *
 * <I>Special Notes</I>
 */
static OS_STATUS
lwpmudrv_Read_VISA_Counts (
    PVOID         out_buf,
    U32           out_buf_len
)
{
    if (out_buf == NULL) {
        SEP_PRINT_ERROR("lwpmudrv_Read_VISA_Counts: VISA buffer is NULL\n");
        return OS_FAULT;
    }
#if defined(DRV_IA32) || defined(DRV_EM64T)
    if (dispatch_visa && dispatch_visa->read_current_data) {
        dispatch_visa->read_current_data(out_buf);
    }
#endif

    return OS_SUCCESS;
}



/* ------------------------------------------------------------------------- */
/*!
 * @fn static OS_STATUS lwpmudrv_Create_Lakemore_Mem(IOCTL_ARGS arg)
 *
 * @param - none
 *
 * @return - OS_STATUS
 *
 * @brief Read the Counter Data.
 *
 * <I>Special Notes</I>
 */
static OS_STATUS
lwpmudrv_Create_Lakemore_Mem (
    IOCTL_ARGS arg
)
{
    U32   memory_size           = 0;
    U64   lakemore_phys_address = 0;

    if (arg->w_buf == NULL || arg->w_len == 0) {
        SEP_PRINT_ERROR("lwpmudrv_Create_Lakemore_Mem: VISA buffer is NULL\n");
        return OS_FAULT;
    }

    if (copy_from_user(&memory_size, (U32*)arg->w_buf, sizeof(U32))) {
        return OS_FAULT;
    }

    if (arg->r_buf == NULL) {
        SEP_PRINT_ERROR("lwpmudrv_Create_Lakemore_Mem: output buffer is NULL\n");
        return OS_FAULT;
    }
    SEP_PRINT_DEBUG("Read size=%llx\n", arg->r_len);
    SEP_PRINT_DEBUG("Write size=%llx\n", arg->w_len);
    if (arg->r_len != sizeof(U64)) {
        return OS_FAULT;
    }
    if ((arg->r_len != sizeof(U64)) || (arg->r_buf == NULL)) {
        return OS_FAULT;
    }

    dispatch_visa = LWPMU_DEVICE_dispatch(device_visa);
    if (dispatch_visa && dispatch_visa->create_lakemore_mem) {
        dispatch_visa->create_lakemore_mem(memory_size, &lakemore_phys_address);
    }
    else {
        SEP_PRINT_ERROR("dispatch table could not be called\n");
    }

    if (copy_to_user(arg->r_buf, (void*)&lakemore_phys_address, sizeof(U64))) {
        return OS_FAULT;
    }

    return OS_SUCCESS;
}


/* ------------------------------------------------------------------------- */
/*!
 * @fn static OS_STATUS lwpmudrv_Check_Lakemore_Status( IOCTL_ARGS arg)
 *
 * @param - none
 *
 * @return - OS_STATUS
 *
 * @brief Read the Counter Data.
 *
 * <I>Special Notes</I>
 */
static OS_STATUS
lwpmudrv_Check_Lakemore_Status (
    IOCTL_ARGS arg
)
{
    U32   num_entries = 0;
    U64  *status_data = 0;

    if ((arg->r_len == 0) || (arg->r_buf == NULL)) {
        return OS_FAULT;
    }

    status_data = CONTROL_Allocate_Memory(arg->r_len);
    if (dispatch_visa && dispatch_visa->check_lakemore_status) {
        dispatch_visa->check_lakemore_status(status_data,  &num_entries);
    }

    if (copy_to_user(arg->r_buf, (void*)status_data, num_entries*sizeof(U64))) {
        return OS_FAULT;
    }
    CONTROL_Free_Memory(status_data);

    return OS_SUCCESS;
}


/* ------------------------------------------------------------------------- */
/*!
 * @fn static OS_STATUS lwpmudrv_Read_Lakemore_Mem( IOCTL_ARGS arg)
 *
 * @param - none
 *
 * @return - OS_STATUS
 *
 * @brief Read the Counter Data.
 *
 * <I>Special Notes</I>
 */
static OS_STATUS
lwpmudrv_Read_Lakemore_Mem (
 IOCTL_ARGS  arg
)
{
    U64   start_address   = 0;
    U64  *mem_address     = NULL;
    U32   mem_size        = 0;
    U32   num_entries     = 0;

     if (arg->w_buf == NULL || arg->w_len == 0) {
        SEP_PRINT_ERROR("lwpmudrv_Create_Lakemore_Mem: VISA buffer is NULL\n");
        return OS_FAULT;
    }

    if (copy_from_user(&start_address, (U64*)arg->w_buf, sizeof(U64))) {
        return OS_FAULT;
    }

    if ((arg->r_len == 0) || (arg->r_buf == NULL)) {
        return OS_FAULT;
    }
    mem_size = (U32) arg->r_len;
    mem_address = CONTROL_Allocate_Memory(mem_size);
    num_entries = (U32)(mem_size/sizeof(U64));
    if (dispatch_visa && dispatch_visa->read_lakemore_mem) {
        dispatch_visa->read_lakemore_mem(start_address, mem_address, num_entries);
    }
    if (copy_to_user(arg->r_buf, (void*)mem_address, mem_size)) {
        return OS_FAULT;
    }
    CONTROL_Free_Memory(mem_address);

    return OS_SUCCESS;
}


/* ------------------------------------------------------------------------- */
/*!
 * @fn static VOID lwpmudrv_Stop_ODLA(void)
 *
 * @param - none
 *
 * @return - none
 *
 * @brief Stop Lakemore ODLA
 *
 * <I>Special Notes</I>
 */
extern VOID
lwpmudrv_Stop_ODLA (
    VOID
)
{
    SEP_PRINT_DEBUG("Entered Stop ODLA\n");

    if (dispatch_visa && dispatch_visa->stop_lakemore) {
        dispatch_visa->stop_lakemore();
    }

    SEP_PRINT_DEBUG("Exited Stop ODLA\n");

    return;
}


/*******************************************************************************
 *  External Driver functions - Open
 *      This function is common to all drivers
 *******************************************************************************/

static int
visa_Open (
    struct inode *inode,
    struct file  *filp
)
{
    SEP_PRINT_DEBUG("lwpmu_Open called on maj:%d, min:%d\n",
            imajor(inode), iminor(inode));
    filp->private_data = container_of(inode->i_cdev, LWPMU_DEV_NODE, cdev);

    return 0;
}

/*******************************************************************************
 *  External Driver functions
 *      These functions are registered into the file operations table that
 *      controls this device.
 *      Open, Close, Read, Write, Release
 *******************************************************************************/

static ssize_t
visa_Read (
    struct file  *filp,
    char         *buf,
    size_t        count,
    loff_t       *f_pos
)
{
    unsigned long retval;

    /* Transfering data to user space */
    SEP_PRINT_DEBUG("lwpmu_Read dispatched with count=%d\n", (S32)count);
    if (copy_to_user(buf, &LWPMU_DEV_buffer(visa_control), 1)) {
        retval = OS_FAULT;
        return retval;
    }
    /* Changing reading position as best suits */
    if (*f_pos == 0) {
        *f_pos+=1;
        return 1;
    }

    return 0;
}

static ssize_t
visa_Write (
    struct file  *filp,
    const  char  *buf,
    size_t        count,
    loff_t       *f_pos
)
{
    unsigned long retval;

    SEP_PRINT_DEBUG("lwpmu_Write dispatched with count=%d\n", (S32)count);
    if (copy_from_user(&LWPMU_DEV_buffer(visa_control), buf+count-1, 1)) {
        retval = OS_FAULT;
        return retval;
    }

    return 1;
}

/* ------------------------------------------------------------------------- */
/*!
 * @fn  extern IOCTL_OP_TYPE lwpmu_Service_IOCTL(IOCTL_USE_NODE, filp, cmd, arg)
 *
 * @param   IOCTL_USE_INODE       - Used for pre 2.6.32 kernels
 * @param   struct   file   *filp - file pointer
 * @param   unsigned int     cmd  - IOCTL command
 * @param   unsigned long    arg  - args to the IOCTL command
 *
 * @return OS_STATUS
 *
 * @brief  Worker function that handles IOCTL requests from the user mode.
 *
 * <I>Special Notes</I>
 */
extern IOCTL_OP_TYPE
lwpmu_Service_IOCTL (
    IOCTL_USE_INODE
    struct   file   *filp,
    unsigned int     cmd,
    IOCTL_ARGS_NODE  local_args
)
{
    int status = OS_SUCCESS;

    switch (cmd) {

       /*
        * Common IOCTL commands
        */
        case  DRV_OPERATION_VERSION:
            SEP_PRINT_DEBUG(" DRV_OPERATION_VERSION\n");
            status = lwpmudrv_Version(&local_args);
            break;

        case  DRV_OPERATION_RESERVE:
            SEP_PRINT_DEBUG(" DRV_OPERATION_RESERVE\n");
            //status = lwpmudrv_Reserve(&local_args);
            break;

        case  DRV_OPERATION_INIT_PMU:
            SEP_PRINT_DEBUG(" DRV_OPERATION_INIT_PMU\n");
            status = lwpmudrv_Init_PMU();
            break;

        case  DRV_OPERATION_START:
            SEP_PRINT_DEBUG(" DRV_OPERATION_START\n");
            status = visa_Start();
            break;

        case  DRV_OPERATION_STOP:
            SEP_PRINT_DEBUG(" DRV_OPERATION_STOP\n");
            status = visa_Prepare_Stop();
            break;

        case  DRV_OPERATION_PAUSE:
            SEP_PRINT_DEBUG(" DRV_OPERATION_PAUSE\n");
            //status = lwpmudrv_Pause();
            break;

        case  DRV_OPERATION_RESUME:
            SEP_PRINT_DEBUG(" DRV_OPERATION_RESUME\n");
            //status = lwpmudrv_Resume();
            break;

        case  DRV_OPERATION_TERMINATE:
            SEP_PRINT_DEBUG(" DRV_OPERATION_TERMINATE\n");
            status = visa_Terminate();
            break;

        case  DRV_OPERATION_INIT_VISA:
            SEP_PRINT_DEBUG(" DRV_OPERATION_INIT_VISA\n");
            status = lwpmudrv_Initialize_Visa(local_args.w_buf, local_args.w_len);
            break;
        case  DRV_OPERATION_EM_GROUPS_VISA:
            SEP_PRINT_DEBUG(" DRV_OPERATION_EM_GROUPS_UNC\n");
            status = lwpmudrv_Set_EM_Config_Visa(&local_args);
            break;

        case  DRV_OPERATION_EM_CONFIG_NEXT_VISA:
            SEP_PRINT_DEBUG(" DRV_OPERATION_EM_CONFIG_NEXT_UNC\n");
            status = visa_Configure_Events_VISA(&local_args);
            break;

        case  DRV_OPERATION_TIMER_TRIGGER_READ:
            lwpmudrv_Trigger_Read();
            break;

       case  DRV_OPERATION_READ_VISA_DATA:
            SEP_PRINT_DEBUG(" DRV_OPERATION_READ_VISA_DATA\n");
            status = lwpmudrv_Read_VISA_Counts(local_args.r_buf, local_args.r_len);
            break;


        case  DRV_OPERATION_CREATE_LAKEMORE_MEM:
            SEP_PRINT_DEBUG(" DRV_OPERATION_CREATE_LAKEMORE_MEM\n");
            lwpmudrv_Create_Lakemore_Mem(&local_args);
            break;

        case  DRV_OPERATION_READ_LAKEMORE_MEM:
            SEP_PRINT_DEBUG(" DRV_OPERATION_READ_LAKEMORE_MEM\n");
            lwpmudrv_Read_Lakemore_Mem(&local_args);
            break;

        case  DRV_OPERATION_CHECK_LAKEMORE_STATUS:
            SEP_PRINT_DEBUG(" DRV_OPERATION_CHECK_LAKEMORE_STATUS\n");
            lwpmudrv_Check_Lakemore_Status(&local_args);
            break;

        case  DRV_OPERATION_STOP_ODLA:
            SEP_PRINT_DEBUG(" DRV_OPERATION_STOP_ODLA\n");
            lwpmudrv_Stop_ODLA();
            break;

       /*
        * if none of the above, treat as unknown/illegal IOCTL command
        */
        default:
            SEP_PRINT_ERROR("Unknown IOCTL magic:%d number:%d\n",
                    _IOC_TYPE(cmd), _IOC_NR(cmd));
            status = OS_ILLEGAL_IOCTL;
            break;
    }

    if (cmd ==  DRV_OPERATION_STOP &&
        GLOBAL_STATE_current_phase(driver_state) == DRV_STATE_PREPARE_STOP) {
        status = visa_Finish_Stop();
    }

    return status;
}

extern long
lwpmu_Device_Control (
    IOCTL_USE_INODE
    struct   file   *filp,
    unsigned int     cmd,
    unsigned long    arg
)
{
    int              status = OS_SUCCESS;
    IOCTL_ARGS_NODE  local_args;

#if !defined(DRV_USE_UNLOCKED_IOCTL)
    SEP_PRINT_DEBUG("lwpmu_DeviceControl(0x%x) called on inode maj:%d, min:%d\n",
            cmd, imajor(inode), iminor(inode));
#endif
    SEP_PRINT_DEBUG("type: %d, subcommand: %d\n", _IOC_TYPE(cmd), _IOC_NR(cmd));

    if (_IOC_TYPE(cmd) != LWPMU_IOC_MAGIC) {
        SEP_PRINT_ERROR("Unknown IOCTL magic:%d\n", _IOC_TYPE(cmd));
        return OS_ILLEGAL_IOCTL;
    }

    MUTEX_LOCK(ioctl_lock);
    if (arg) {
        status = copy_from_user(&local_args, (IOCTL_ARGS)arg, sizeof(IOCTL_ARGS_NODE));
    }

    status = lwpmu_Service_IOCTL (IOCTL_USE_INODE filp, _IOC_NR(cmd), local_args);
    MUTEX_UNLOCK(ioctl_lock);

    return  status;
}


#if defined(HAVE_COMPAT_IOCTL) && defined(DRV_EM64T)
extern long
lwpmu_Device_Control_Compat (
    struct   file   *filp,
    unsigned int     cmd,
    unsigned long    arg
)
{
    int                     status = OS_SUCCESS;
    IOCTL_COMPAT_ARGS_NODE  local_args_compat;
    IOCTL_ARGS_NODE         local_args;

    memset(&local_args_compat, 0, sizeof(IOCTL_COMPAT_ARGS_NODE));
    SEP_PRINT_DEBUG("Compat: type: %d, subcommand: %d\n", _IOC_TYPE(cmd), _IOC_NR(cmd));

    if (_IOC_TYPE(cmd) != LWPMU_IOC_MAGIC) {
        SEP_PRINT_ERROR("Unknown IOCTL magic:%d\n", _IOC_TYPE(cmd));
        return OS_ILLEGAL_IOCTL;
    }

    MUTEX_LOCK(ioctl_lock);
    if (arg) {
        status = copy_from_user(&local_args_compat, (IOCTL_COMPAT_ARGS)arg, sizeof(IOCTL_COMPAT_ARGS_NODE));
    }
    local_args.r_len = local_args_compat.r_len;
    local_args.w_len = local_args_compat.w_len;
    local_args.r_buf = (char *) compat_ptr(local_args_compat.r_buf);
    local_args.w_buf = (char *) compat_ptr(local_args_compat.w_buf);

    status = lwpmu_Service_IOCTL (filp, _IOC_NR(cmd), local_args);
    MUTEX_UNLOCK(ioctl_lock);

    return status;
}
#endif

/*
 * @fn        LWPMUDRV_Abnormal_Terminate(void)
 *
 * @brief     This routine is called from linuxos_Exit_Task_Notify if the user process has
 *            been killed by an uncatchable signal (example kill -9).  The state variable
 *            abormal_terminate is set to 1 and the clean up routines are called.  In this
 *            code path the OS notifier hooks should not be unloaded.
 *
 * @param     None
 *
 * @return    OS_STATUS
 *
 * <I>Special Notes:</I>
 *     <none>
 */
extern int
LWPMUDRV_Abnormal_Terminate (
    void
)
{
    int              status = OS_SUCCESS;

    abnormal_terminate = 1;
    SEP_PRINT_DEBUG("Abnormal-Termination: Calling visa_Prepare_Stop\n");
    status = visa_Prepare_Stop();
    SEP_PRINT_DEBUG("Abnormal-Termination: Calling visa_Finish_Stop\n");
    status = visa_Finish_Stop();
    SEP_PRINT_DEBUG("Abnormal-Termination: Calling lwpmudrv_Terminate\n");
    status = visa_Terminate();

    return status;
}


/*****************************************************************************************
 *
 *   Driver Entry / Exit functions that will be called on when the driver is loaded and
 *   unloaded
 *
 ****************************************************************************************/

/*
 * Structure that declares the usual file access functions
 * First one is for lwpmu_c, the control functions
 */
static struct file_operations visa_Fops = {
    .owner =   THIS_MODULE,
    IOCTL_OP = lwpmu_Device_Control,
#if defined(HAVE_COMPAT_IOCTL) && defined(DRV_EM64T)
    .compat_ioctl = lwpmu_Device_Control_Compat,
#endif
    .read =    visa_Read,
    .write =   visa_Write,
    .open =    visa_Open,
    .release = NULL,
    .llseek =  NULL,
};

/*!
 * @fn  static int lwpmudrv_setup_cdev(dev, fops, dev_number)
 *
 * @param LWPMU_DEV               dev  - pointer to the device object
 * @param struct file_operations *fops - pointer to the file operations struct
 * @param dev_t                   dev_number - major/monor device number
 *
 * @return OS_STATUS
 *
 * @brief  Set up the device object.
 *
 * <I>Special Notes</I>
 */
static int
lwpmu_setup_cdev (
    LWPMU_DEV               dev,
    struct file_operations *fops,
    dev_t                   dev_number
)
{
    cdev_init(&LWPMU_DEV_cdev(dev), fops);
    LWPMU_DEV_cdev(dev).owner = THIS_MODULE;
    LWPMU_DEV_cdev(dev).ops   = fops;

    return cdev_add(&LWPMU_DEV_cdev(dev), dev_number, 1);
}

/* ------------------------------------------------------------------------- */
/*!
 * @fn  static int visa_Load(void)
 *
 * @param none
 *
 * @return STATUS
 *
 * @brief  Load the driver module into the kernel.  Set up the driver object.
 * @brief  Set up the initial state of the driver and allocate the memory
 * @brief  needed to keep basic state information.
 */
static int
visa_Load (
    VOID
)
{
    int        num_cpus;
    OS_STATUS  status      = OS_SUCCESS;

    CONTROL_Memory_Tracker_Init();

    /* Get one major device number and two minor numbers. */
    /*   The result is formatted as major+minor(0) */
    /*   One minor number is for control (lwpmu_c), */
    /*   the other (lwpmu_m) is for modules */
    SEP_PRINT("lwpmu driver loading...\n");
    SEP_PRINT("lwpmu driver about to register chrdev...\n");

    lwpmu_DevNum = MKDEV(0, 0);
    status = alloc_chrdev_region(&lwpmu_DevNum, 0, PMU_DEVICES, SEP_DRIVER_NAME);
    SEP_PRINT("result of alloc_chrdev_region is %d\n", status);
    if (status<0) {
        SEP_PRINT_ERROR("lwpmu driver failed to alloc chrdev_region!\n");
        return status;
    }
    SEP_PRINT("lwpmu driver: major number is %d\n", MAJOR(lwpmu_DevNum));
    status = lwpmudrv_Initialize_State();
    if (status<0) {
        SEP_PRINT_ERROR("lwpmu driver failed to initialize state!\n");
        return status;
    }
    num_cpus = GLOBAL_STATE_num_cpus(driver_state);
    SEP_PRINT("detected %d CPUs in lwpmudrv_Load\n", num_cpus);

    /* Allocate memory for the control structures */
    visa_control = CONTROL_Allocate_Memory(sizeof(LWPMU_DEV_NODE));

    if (!visa_control) {
        CONTROL_Free_Memory(visa_control);
        return OS_NO_MEM;
    }

    /* Register the file operations with the OS */

#if defined (DRV_ANDROID) || defined (DRV_CHROMEOS)
    SEP_PRINT("ANDROID_DEVICE %s...\n", SEP_DRIVER_NAME DRV_DEVICE_DELIMITER"c");
    pmu_class = class_create(THIS_MODULE, SEP_DRIVER_NAME);
    if (IS_ERR(pmu_class)) {
        SEP_PRINT_ERROR("Error registering SEP control class\n");
    }
    device_create(pmu_class, NULL, lwpmu_DevNum, NULL, SEP_DRIVER_NAME DRV_DEVICE_DELIMITER"c");
#endif

    status = lwpmu_setup_cdev(visa_control,&visa_Fops,lwpmu_DevNum);
    if (status) {
        SEP_PRINT_ERROR("Error %d adding lwpmu as char device\n", status);
        return status;
    }

    //pcb_size            = GLOBAL_STATE_num_cpus(driver_state)*sizeof(CPU_STATE_NODE);
    //pcb                 = CONTROL_Allocate_Memory(pcb_size);

    MUTEX_INIT(ioctl_lock);

    /*
     *  Initialize the VISA driver version (done once at driver load time)
     */
    SEP_VERSION_NODE_major(&drv_version) = SEP_MAJOR_VERSION;
    SEP_VERSION_NODE_minor(&drv_version) = SEP_MINOR_VERSION;
    SEP_VERSION_NODE_api(&drv_version)   = SEP_API_VERSION;
    //
    // Display driver version information
    //
    SEP_PRINT("VISA collection driver v%d.%d.%d has been loaded.\n",
              SEP_VERSION_NODE_major(&drv_version),
              SEP_VERSION_NODE_minor(&drv_version),
              SEP_VERSION_NODE_api(&drv_version));

    return status;
}

/* ------------------------------------------------------------------------- */
/*!
 * @fn  static int lwpmu_Unload(void)
 *
 * @param none
 *
 * @return none
 *
 * @brief  Remove the driver module from the kernel.
 */
static VOID
visa_Unload (
    VOID
)
{
    SEP_PRINT("lwpmu driver unloading...\n");

    pcb                 = CONTROL_Free_Memory(pcb);
    pcb_size            = 0;

#if defined (DRV_ANDROID) || defined (DRV_CHROMEOS)
    unregister_chrdev(MAJOR(lwpmu_DevNum), SEP_DRIVER_NAME);
    device_destroy(pmu_class, lwpmu_DevNum);
    device_destroy(pmu_class, lwpmu_DevNum+1);
#endif

    cdev_del(&LWPMU_DEV_cdev(visa_control));
    unregister_chrdev_region(lwpmu_DevNum, PMU_DEVICES);

#if defined (DRV_ANDROID) || defined (DRV_CHROMEOS)
    class_destroy(pmu_class);
#endif

    visa_control  = CONTROL_Free_Memory(visa_control);

    CONTROL_Memory_Tracker_Free();

    //
    // Display driver version information
    //
    SEP_PRINT("VISA collection driver has been unloaded.\n");

    //
    // Display driver version information
    //
    SEP_PRINT("VISA driver v%d.%d.%d has been unloaded.\n",
              SEP_VERSION_NODE_major(&drv_version),
              SEP_VERSION_NODE_minor(&drv_version),
              SEP_VERSION_NODE_api(&drv_version));

    return;
}

/* Declaration of the init and exit functions */
module_init(visa_Load);
module_exit(visa_Unload);
