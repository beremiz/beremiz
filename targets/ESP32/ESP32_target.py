#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..toolchain_gcc import toolchain_gcc
from util.ProcessLogger import ProcessLogger
import os
import subprocess
import shutil
import wx


class ESP32OptionsDialog(wx.Dialog):
    def __init__(self, parent, default_idf, default_port, default_flash, default_chip="esp32c"):
        super().__init__(parent, title="Opciones ESP32", size=(400, 250))

        panel = wx.Panel(self)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # IDF Path
        idf_sizer = wx.BoxSizer(wx.HORIZONTAL)
        idf_label = wx.StaticText(panel, label="IDF_PATH:")
        self.idf_ctrl = wx.TextCtrl(panel, value=default_idf, size=(250, -1))
        browse_btn = wx.Button(panel, label="...")
        browse_btn.Bind(wx.EVT_BUTTON, self.OnBrowse)
        idf_sizer.Add(idf_label, 0, wx.ALL | wx.CENTER, 5)
        idf_sizer.Add(self.idf_ctrl, 1, wx.ALL, 5)
        idf_sizer.Add(browse_btn, 0, wx.ALL, 5)
        main_sizer.Add(idf_sizer, 0, wx.EXPAND)

        # Puerto
        port_sizer = wx.BoxSizer(wx.HORIZONTAL)
        port_label = wx.StaticText(panel, label="Puerto:")
        self.port_ctrl = wx.TextCtrl(panel, value=default_port)
        port_sizer.Add(port_label, 0, wx.ALL | wx.CENTER, 5)
        port_sizer.Add(self.port_ctrl, 1, wx.ALL, 5)
        main_sizer.Add(port_sizer, 0, wx.EXPAND)

        # Flash checkbox
        self.flash_cb = wx.CheckBox(panel, label="Hacer flash")
        self.flash_cb.SetValue(default_flash)
        main_sizer.Add(self.flash_cb, 0, wx.ALL, 5)

        # Chip selection
        chip_sizer = wx.BoxSizer(wx.HORIZONTAL)
        chip_label = wx.StaticText(panel, label="Chip:")
        chip_choices = ["esp32c", "esp32s2", "esp32s3", "esp32c3"]
        self.chip_choice = wx.ComboBox(panel, choices=chip_choices, style=wx.CB_READONLY)
        self.chip_choice.SetValue(default_chip)
        chip_sizer.Add(chip_label, 0, wx.ALL | wx.CENTER, 5)
        chip_sizer.Add(self.chip_choice, 1, wx.ALL, 5)
        main_sizer.Add(chip_sizer, 0, wx.EXPAND)

        # Botones Aceptar/Cancelar
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        panel.SetSizer(main_sizer)

    def OnBrowse(self, event):
        dlg = wx.DirDialog(self, "Selecciona carpeta ESP-IDF")
        if dlg.ShowModal() == wx.ID_OK:
            self.idf_ctrl.SetValue(dlg.GetPath())
        dlg.Destroy()




class ESP32_target(toolchain_gcc):
    """
    Target para ESP32 usando ESP-IDF
    """
    extension = ".elf"
    build_dir = "build"
    project_dir = "esp32_project"  # directorio temporal del proyecto ESP-IDF

    def getBuilderCFLAGS(self):
        """
        Retorna los CFLAGS para ESP32
        """
        # Incluye flags típicos de ESP-IDF
        additional_cflags = [
            "-mlongcalls",
            "-ffunction-sections",
            "-fdata-sections",
            "-Wall"
        ]
        # Si quieres activar warnings menos estrictos
        # additional_cflags.append("-Wno-unused-function")
        return toolchain_gcc.getBuilderCFLAGS(self) + additional_cflags

    def getBuilderLDFLAGS(self):
        """
        Retorna los LDFLAGS para ESP32
        """
        additional_ldflags = [
            "-Wl,--gc-sections"
        ]
        return toolchain_gcc.getBuilderLDFLAGS(self) + additional_ldflags
            
    def build(self):
        # Valores por defecto que ya usas
        default_idf = "/home/netza/esp/esp-idf"
        default_port = "/dev/ttyUSB0"
        default_flash = True

        # Mostrar diálogo con valores por defecto
        dlg = ESP32OptionsDialog(None, default_idf, default_port, default_flash)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return False

        idf_path = dlg.idf_ctrl.GetValue()
        flash_port = dlg.port_ctrl.GetValue()
        do_flash = dlg.flash_cb.GetValue()
        chip = dlg.chip_choice.GetValue()
        os.environ["IDF_TARGET"] = chip

        dlg.Destroy()

        export_sh = os.path.join(idf_path, "export.sh")
        # ... resto del build

        beremiz_build = os.path.join(os.getcwd(), "exemples", "target_esp32", "build")
        if not os.path.exists(beremiz_build):
            self.CTRInstance.logger.write_error(f"Error: {beremiz_build} no existe\n")
            return False

        # Proyecto ESP-IDF
        project_path = os.path.join(beremiz_build, "ESP32Projects")
        main_path = os.path.join(project_path, "main")
        components_path = os.path.join(project_path, "components")
        beremiz_component_path = os.path.join(components_path, "beremiz_runtime")
        generated_path = os.path.join(beremiz_component_path, "generated")
        port_path = os.path.join(beremiz_component_path, "port")

        os.makedirs(generated_path, exist_ok=True)
        os.makedirs(main_path, exist_ok=True)
        os.makedirs(port_path, exist_ok=True)

        # ------------------------------------------------------------------
        # Copiar código generado por Beremiz
        # ------------------------------------------------------------------
        copied_any = False
        for f in os.listdir(beremiz_build):
            if f.endswith(".c") or f.endswith(".h"):
                shutil.copy(os.path.join(beremiz_build, f), generated_path)
                copied_any = True

        if not copied_any:
            self.CTRInstance.logger.write_error("No se encontraron archivos C generados por Beremiz.\n")
            return False

        # ------------------------------------------------------------------
        # LIMPIEZA AUTOMÁTICA DE TYPEDEFS CONFLICTIVOS
        # ------------------------------------------------------------------
        for root, dirs, files in os.walk(generated_path):
            for file in files:
                if file.endswith(".c") or file.endswith(".h"):
                    filepath = os.path.join(root, file)

                    with open(filepath, "r") as f:
                        content = f.read()

                    content = content.replace("typedef unsigned int uint32_t;", "")
                    content = content.replace("typedef unsigned long uint32_t;", "")
                    content = content.replace("typedef unsigned short uint16_t;", "")
                    content = content.replace("typedef unsigned char uint8_t;", "")

                    with open(filepath, "w") as f:
                        f.write(content)
        # ------------------------------------------------------------------
        # FORZAR INCLUDE DE POUS.h Y pyext_stub.h EN TODOS LOS .c
        # ------------------------------------------------------------------
        for root, dirs, files in os.walk(generated_path):
            for file in files:
                if file.endswith(".c"):
                    filepath = os.path.join(root, file)

                    with open(filepath, "r") as f:
                        content = f.read()

                    if '#include "POUS.h"' not in content:
                        content = '#include "POUS.h"\n' + content

                    if '#include "pyext_stub.h"' not in content:
                        content = '#include "pyext_stub.h"\n' + content

                    with open(filepath, "w") as f:
                        f.write(content)


        # ------------------------------------------------------------------
        # Crear capa PORT
        # ------------------------------------------------------------------

        with open(os.path.join(port_path, "esp32_port.h"), "w") as f:
            f.write("""#pragma once
    #include "pyext_stub.h"
    #include <stdint.h>
    #include <stdbool.h>
    """)

        with open(os.path.join(port_path, "esp32_atomic.c"), "w") as f:
            f.write("""#include <stdint.h>
    #include <stdbool.h>

    uint32_t AtomicCompareExchange(uint32_t *addr,
                                   uint32_t compare,
                                   uint32_t exchange)
    {
        __atomic_compare_exchange_n(
            addr,
            &compare,
            exchange,
            false,
            __ATOMIC_SEQ_CST,
            __ATOMIC_SEQ_CST
        );
        return compare;
    }
    """)

        with open(os.path.join(port_path, "pyext_stub.h"), "w") as f:
                    f.write("""
            #ifndef PYEXT_STUB_H
        #define PYEXT_STUB_H

        #include "iec_types.h"

        IEC_INT* __GET_GLOBAL_PYEXT_CSV_UPDATE(void);
        IEC_INT* __GET_GLOBAL_CSV_REFRESH(void);
        IEC_INT* __GET_GLOBAL_CSV_UPDATE(void);

        #endif
            """)


        with open(os.path.join(port_path, "pyext_stub.c"), "w") as f:
            f.write("""
        #include <stdint.h>
        #include "iec_types_all.h"

    /* Variables IEC reales */
    static IEC_INT pyext_csv_update_var = 0;
    static IEC_INT csv_refresh_var = 0;
    static IEC_INT csv_update_var = 0;

    /* Getters que retornan punteros */
    IEC_INT* __GET_GLOBAL_PYEXT_CSV_UPDATE(void) {
        return &pyext_csv_update_var;
    }

    IEC_INT* __GET_GLOBAL_CSV_REFRESH(void) {
        return &csv_refresh_var;
    }

    IEC_INT* __GET_GLOBAL_CSV_UPDATE(void) {
        return &csv_update_var;
    }
        """)
        # ------------------------------------------------------------------
        # CMakeLists raíz
        # ------------------------------------------------------------------
        root_cmake = os.path.join(project_path, "CMakeLists.txt")
        if not os.path.exists(root_cmake):
            with open(root_cmake, "w") as f:
                f.write("""cmake_minimum_required(VERSION 3.16)
    include($ENV{IDF_PATH}/tools/cmake/project.cmake)
    project(esp32_project)
    """)

        # ------------------------------------------------------------------
        # main.c mínimo
        # ------------------------------------------------------------------
        main_c = os.path.join(main_path, "main.c")
        if not os.path.exists(main_c):
            with open(main_c, "w") as f:
                f.write("""#include "freertos/FreeRTOS.h"
    #include "freertos/task.h"

    extern void __init(void);
    extern void __run(void);

    static void plc_task(void *arg)
    {
        __init();
        while (1) {
            __run();
            vTaskDelay(pdMS_TO_TICKS(10));
        }
    }

    void app_main(void)
    {
        xTaskCreatePinnedToCore(plc_task, "plc", 8192, NULL, 5, NULL, 1);
    }
    """)

        with open(os.path.join(main_path, "CMakeLists.txt"), "w") as f:
            f.write("""idf_component_register(SRCS "main.c")
    """)

        # ------------------------------------------------------------------
        # CMakeLists del componente beremiz_runtime
        # ------------------------------------------------------------------
        c_files = [f for f in os.listdir(generated_path) if f.endswith(".c")]
        src_lines = "\n        ".join([f'"generated/{f}"' for f in c_files])

        with open(os.path.join(beremiz_component_path, "CMakeLists.txt"), "w") as f:
            f.write(f"""idf_component_register(
        SRCS
            {src_lines}
            "port/esp32_atomic.c"
            "port/pyext_stub.c"
            "esp32_runtime_stub.c"

        INCLUDE_DIRS
            "/home/netza/Beremiz02032026/matiec/lib/C"
            "generated"
            "port"
    )

    target_compile_options(${{COMPONENT_LIB}} PRIVATE
        -Wno-error
        -Wno-unused-function
        -Wno-format
        -Wno-sign-compare
        -Wno-type-limits
        -Wno-pointer-sign
    )
    """)
        with open(os.path.join(beremiz_component_path, "esp32_runtime_stub.c"), "w") as f:
            f.write("""
                    #include <stdint.h>
        #include <stdbool.h>
        /* ================= TIME ================= */

        uint64_t PLC_GetTime(void)
        {
            return 0;
        }

        /* ================= PYTHON (disabled) ================= */

        int TryLockPython(void)
        {
            return 0;
        }

        void UnLockPython(void)
        {
        }

        void UnBlockPythonCommands(void)
        {
        }

        /* ================= RETAIN (disabled) ================= */

        void InitRetain(void)
        {
        }

        int CheckRetainBuffer(void)
        {
            return 0;
        }

        void InValidateRetainBuffer(void)
        {
        }

        void ValidateRetainBuffer(void)
        {
        }

        /* ================= DEBUG (disabled) ================= */

        int TryEnterDebugSection(void)
        {
            return 0;
        }

        void LeaveDebugSection(void)
        {
        }

        void InitiateDebugTransfer(void)
        {
        }
        """)
        

        #idf_path = "/home/netza/esp/esp-idf"
        export_sh = os.path.join(idf_path, "export.sh")
        esp32_project_dir = "/home/netza/Beremiz02032026/beremiz/exemples/target_esp32/build/ESP32Projects"

        # Asegurarte de que IDF_TARGET coincide
        subprocess.call(f"bash -c 'source \"{export_sh}\" && idf.py set-target {chip}'",
                shell=True, cwd=esp32_project_dir)
        # ---------------------
        # Abrir menuconfig
        # ---------------------
        cmd_menuconfig = f"bash -c 'source \"{export_sh}\" && idf.py menuconfig'"
        status_menuconfig = subprocess.call(cmd_menuconfig, shell=True, cwd=esp32_project_dir)
        if status_menuconfig != 0:
            self.CTRInstance.logger.write_error("ESP32 menuconfig cancelled or failed.\n")
            return False

        # ---------------------
        # Build real
        # ---------------------
        cmd_build = f"bash -c 'source \"{export_sh}\" && idf.py build'"

        env = os.environ.copy()
        env["IDF_PATH"] = idf_path

        process = subprocess.Popen(
            cmd_build,
            shell=True,
            cwd=esp32_project_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            print(line, end="")
            self.CTRInstance.logger.write(line)

        process.wait()
        status = process.returncode

        if status != 0:
            self.CTRInstance.logger.write_error("ESP32 build failed!\n")
            return False
        else:
            self.CTRInstance.logger.write("ESP32 build finished successfully.\n")
            return True




















