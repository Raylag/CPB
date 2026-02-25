import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import time
import random
import math
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

matplotlib.use('TkAgg')


class SawSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Имитатор электропилы")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Параметры системы
        self.port1 = 0  # биты: 0-11 данные, 14 готовность, 15 компаратор
        self.port2 = 0
        self.target_width = 1000  # мм, умолчание
        self.cut_duration = 5  # секунд, умолчание
        self.comparator_active = False
        self.cut_end_time = None
        self.current_rpm_code = 93  # код для 10В (5 об/с)
        self.measure_timer = None
        self.first_meas_code = None
        self.second_meas_code = None
        self.voltage_history = []  # список (время, напряжение)
        self.start_time = time.time()
        self.running = True
        self.state = 'IDLE'  # IDLE, MEAS1_WAIT, MEAS2_WAIT, DELAY
        self.meas1_code = 0
        self.meas2_code = 0

        # Создание GUI
        self.create_widgets()

        # Запуск цикла управления
        self.update()

    def create_widgets(self):
        # Панель управления
        control_frame = ttk.Frame(self.root, padding=5)
        control_frame.pack(fill=tk.X)

        self.btn_place_board = ttk.Button(control_frame, text="Положить доску", command=self.place_board)
        self.btn_place_board.pack(side=tk.LEFT, padx=5)

        self.btn_stop = ttk.Button(control_frame, text="Стоп", command=self.stop_cut)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.lbl_state = ttk.Label(control_frame, text="Состояние: Ожидание")
        self.lbl_state.pack(side=tk.LEFT, padx=20)

        # Информационная панель
        info_frame = ttk.LabelFrame(self.root, text="Текущие параметры", padding=5)
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        # Порт 2
        port2_frame = ttk.Frame(info_frame)
        port2_frame.pack(fill=tk.X, pady=2)
        ttk.Label(port2_frame, text="Порт 2 (команды):").pack(side=tk.LEFT)
        self.lbl_port2 = ttk.Label(port2_frame, text="0x0000", font=('Courier', 10))
        self.lbl_port2.pack(side=tk.LEFT, padx=10)
        self.lbl_port2_bits = ttk.Label(port2_frame, text="", font=('Courier', 10))
        self.lbl_port2_bits.pack(side=tk.LEFT)

        # Обороты
        rpm_frame = ttk.Frame(info_frame)
        rpm_frame.pack(fill=tk.X, pady=2)
        ttk.Label(rpm_frame, text="Обороты пилы:").pack(side=tk.LEFT)
        self.lbl_rpm = ttk.Label(rpm_frame, text="5 об/с")
        self.lbl_rpm.pack(side=tk.LEFT, padx=10)

        # Напряжение
        volt_frame = ttk.Frame(info_frame)
        volt_frame.pack(fill=tk.X, pady=2)
        ttk.Label(volt_frame, text="Напряжение мотора:").pack(side=tk.LEFT)
        self.lbl_voltage = ttk.Label(volt_frame, text="10 В")
        self.lbl_voltage.pack(side=tk.LEFT, padx=10)

        # Датчики
        sens_frame = ttk.Frame(info_frame)
        sens_frame.pack(fill=tk.X, pady=2)
        ttk.Label(sens_frame, text="Датчики L:").pack(side=tk.LEFT)
        self.lbl_sens1 = ttk.Label(sens_frame, text="---")
        self.lbl_sens1.pack(side=tk.LEFT, padx=5)
        self.lbl_sens2 = ttk.Label(sens_frame, text="---")
        self.lbl_sens2.pack(side=tk.LEFT, padx=5)

        # График напряжения
        graph_frame = ttk.LabelFrame(self.root, text="График напряжения на моторе", padding=5)
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.fig = Figure(figsize=(6, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Время (с)")
        self.ax.set_ylabel("Напряжение (В)")
        self.ax.grid(True)
        self.line, = self.ax.plot([], [], 'b-')
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Добавим начальную точку
        self.add_voltage_point(10.0)

    def place_board(self):
        if self.comparator_active:
            messagebox.showinfo("Информация", "Сейчас уже идет распил. Дождитесь окончания.")
            return
        # Диалог ввода
        dialog = tk.Toplevel(self.root)
        dialog.title("Параметры доски")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Ширина листа (мм):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        entry_width = ttk.Entry(dialog)
        entry_width.grid(row=0, column=1, padx=5, pady=5)
        entry_width.insert(0, str(self.target_width))

        ttk.Label(dialog, text="Время распила (с):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        entry_time = ttk.Entry(dialog)
        entry_time.grid(row=1, column=1, padx=5, pady=5)
        entry_time.insert(0, str(self.cut_duration))

        def on_ok():
            try:
                w = float(entry_width.get())
                t = float(entry_time.get())
                if w <= 0 or t <= 0:
                    raise ValueError
                self.target_width = w
                self.cut_duration = t
                dialog.destroy()
                self.start_cut()
            except:
                messagebox.showerror("Ошибка", "Введите положительные числа")

        ttk.Button(dialog, text="OK", command=on_ok).grid(row=2, column=0, columnspan=2, pady=10)

    def start_cut(self):
        self.comparator_active = True
        self.cut_end_time = time.time() + self.cut_duration
        self.btn_place_board.config(state=tk.DISABLED)
        self.lbl_state.config(text="Состояние: Распил")
        # Запускаем таймер окончания
        self.root.after(int(self.cut_duration * 1000), self.finish_cut)

    def finish_cut(self):
        self.comparator_active = False
        self.cut_end_time = None
        self.btn_place_board.config(state=tk.NORMAL)
        self.lbl_state.config(text="Состояние: Ожидание")

    def stop_cut(self):
        if self.comparator_active:
            self.comparator_active = False
            self.cut_end_time = None
            self.btn_place_board.config(state=tk.NORMAL)
            self.lbl_state.config(text="Состояние: Ожидание (прервано)")

    def out_port2(self, value):
        """Запись в порт 2 (управление)"""
        self.port2 = value
        self.update_port2_display()

        # Анализ команд
        # Команда первого измерения (биты 15 и 14)
        if (value & 0xC000) == 0xC000:
            # Сброс готовности
            self.port1 &= ~0x4000
            # Отмена предыдущего таймера
            if self.measure_timer:
                self.root.after_cancel(self.measure_timer)
            # Запуск нового измерения через случайное время
            delay = random.uniform(0.05, 0.2) * 1000  # мс
            self.measure_timer = self.root.after(int(delay), lambda: self.set_measurement(1))
        # Команда второго измерения (биты 14 и 13)
        elif (value & 0x6000) == 0x6000:
            self.port1 &= ~0x4000
            if self.measure_timer:
                self.root.after_cancel(self.measure_timer)
            delay = random.uniform(0.05, 0.2) * 1000
            self.measure_timer = self.root.after(int(delay), lambda: self.set_measurement(2))
        # Команда установки оборотов (бит14=1, биты15 и13=0)
        elif (value & 0x4000) and not (value & 0x8000) and not (value & 0x2000):
            code = value & 0x03FF  # 10 бит
            self.current_rpm_code = code
            voltage = code * 110.0 / 1023.0
            self.add_voltage_point(voltage)
            self.update_rpm_display()

    def set_measurement(self, meas_num):
        """Установка результата измерения"""
        # Генерация кода на основе target_width с небольшим шумом
        # Шум: нормальное отклонение до ±5 мм
        noise = random.gauss(0, 2)
        L = self.target_width + noise
        L = max(0, min(4096, L))  # ограничение диапазона
        code = int(round(L / 4096.0 * 4095))
        code = max(0, min(4095, code))

        # Устанавливаем в порт1
        self.port1 = (self.port1 & ~0x4FFF) | code | 0x4000  # бит14=1, данные

        if meas_num == 1:
            self.first_meas_code = code
        else:
            self.second_meas_code = code
        self.update_sensors_display()
        self.measure_timer = None

    def in_port1(self):
        """Чтение порта 1"""
        return self.port1

    def add_voltage_point(self, voltage):
        """Добавление точки на график напряжения"""
        current_time = time.time() - self.start_time
        self.voltage_history.append((current_time, voltage))
        # Оставляем только последние 100 точек для наглядности
        if len(self.voltage_history) > 100:
            self.voltage_history.pop(0)
        # Обновление графика
        times, volts = zip(*self.voltage_history)
        self.line.set_data(times, volts)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

    def update_port2_display(self):
        """Обновление отображения порта 2"""
        hex_str = f"0x{self.port2:04X}"
        bits = f"биты: {self.port2>>15 &1} {self.port2>>14 &1} {self.port2>>13 &1}  код={self.port2 & 0x03FF}"
        self.lbl_port2.config(text=hex_str)
        self.lbl_port2_bits.config(text=bits)

    def update_rpm_display(self):
        """Обновление отображения оборотов и напряжения"""
        code = self.current_rpm_code
        voltage = code * 110.0 / 1023.0
        rpm = voltage / 2.0  # 10В = 5 об/с, значит 2В = 1 об/с
        self.lbl_voltage.config(text=f"{voltage:.1f} В")
        self.lbl_rpm.config(text=f"{rpm:.1f} об/с")

    def update_sensors_display(self):
        """Обновление показаний датчиков"""
        if self.first_meas_code is not None:
            L1 = self.first_meas_code * 4096.0 / 4095.0
            self.lbl_sens1.config(text=f"1: {L1:.1f} мм")
        if self.second_meas_code is not None:
            L2 = self.second_meas_code * 4096.0 / 4095.0
            self.lbl_sens2.config(text=f"2: {L2:.1f} мм")

    def update(self):
        """Главный цикл управления (вызывается через after)"""
        if not self.running:
            return

        if self.state == 'IDLE':
            if self.comparator_active:
                # Начать первое измерение
                self.out_port2(self.current_rpm_code | 0xC000)  # биты 15,14
                self.state = 'MEAS1_WAIT'
                self.root.after(50, self.update)  # частая проверка
            else:
                # Поддержка холостого хода
                self.out_port2(93 | 0x4000)  # код 10В с битом14
                self.root.after(300, self.update)  # задержка 0.3 с

        elif self.state == 'MEAS1_WAIT':
            if self.port1 & 0x4000:
                # Данные готовы
                self.meas1_code = self.port1 & 0x0FFF
                # Начать второе измерение
                self.out_port2(self.current_rpm_code | 0x6000)  # биты 14,13
                self.state = 'MEAS2_WAIT'
                self.root.after(50, self.update)
            else:
                self.root.after(50, self.update)

        elif self.state == 'MEAS2_WAIT':
            if self.port1 & 0x4000:
                self.meas2_code = self.port1 & 0x0FFF
                # Усреднение
                avg_code = (self.meas1_code + self.meas2_code) // 2
                # Определение нового кода оборотов
                if avg_code < 1000:
                    # оставляем текущий
                    pass
                elif avg_code < 1450:
                    self.current_rpm_code = 558
                elif avg_code < 2200:
                    self.current_rpm_code = 744
                else:
                    self.current_rpm_code = 930
                # Отправка нового кода с битом14
                self.out_port2(self.current_rpm_code | 0x4000)
                self.state = 'DELAY'
                self.root.after(300, self.update)  # задержка 0.3 с
            else:
                self.root.after(50, self.update)

        elif self.state == 'DELAY':
            self.state = 'IDLE'
            self.root.after(0, self.update)

    def on_closing(self):
        self.running = False
        if self.measure_timer:
            self.root.after_cancel(self.measure_timer)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SawSimulator(root)
    root.geometry("800x600")
    root.mainloop()
