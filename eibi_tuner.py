# eibi_tuner v2.0
# ===============
# Created by Peter Betz (DD2ZG) with support of Gemini 2.5
#
import tkinter as tk
from datetime import datetime, timezone
from tkinter import filedialog, Listbox, Scrollbar
import xmlrpc.client

class EibiTuner(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.title("eibi_tuner")
        self.pack(fill=tk.BOTH, expand=True)
        self.mode = "View" # Default mode
        self.after_id = None # To store the ID of the scheduled periodic update
        self.filter_term = tk.StringVar() # To store filter term
        self.filter_term.set("") # Initialize with empty string
        self.all_data_lines = [] # To store all parsed data lines (dictionaries)
        self.current_file_type = None # To store the type of the currently loaded file ("EIBI" or "ILG")
        self.eibi_header_text = "kHZ           Time(UTC) Days  ITU Station                Lang. Target   Remarks"
        self.eibi_column_names = [] # To store column names for EIBI files
        self.eibi_column_widths = {} # To store calculated maximum widths for EIBI columns
        self.ilg_column_names = [] # To store column names for ILG files
        self.ilg_column_widths = {} # To store calculated maximum widths for ILG columns
        self.temp_line_index = -1 # To track the index of the temporary frequency line
        self.displayed_data_items = [] # To store data items currently displayed in the listbox
        self.previous_highlights = [] # To store indices and original colors of previously highlighted items
        self.last_flrig_freq_hz = None
        self.last_update_minute = None
        self.create_widgets()
        self.create_menu()
        # Initialize view mode settings
        self.last_flrig_freq_hz = None
        self.last_update_minute = None
        self.update_listbox_display()
        self.update_utc_time() # Start updating UTC time
        self.update_view_mode_display() # Start updating view mode display

    def create_widgets(self):
        config_frame = tk.Frame(self)
        config_frame.pack(fill=tk.X, padx=5, pady=5)

        host_label = tk.Label(config_frame, text="FLRIG Host:")
        host_label.pack(side=tk.LEFT)
        self.host_entry = tk.Entry(config_frame, width=12, relief=tk.RIDGE, borderwidth=2)
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.pack(side=tk.LEFT)

        port_label = tk.Label(config_frame, text="Port:")
        port_label.pack(side=tk.LEFT)
        self.port_entry = tk.Entry(config_frame, width=4, relief=tk.RIDGE, borderwidth=2)
        self.port_entry.insert(0, "12345")
        self.port_entry.pack(side=tk.LEFT)



        self.active_only_var = tk.BooleanVar()
        self.active_only_check = tk.Checkbutton(config_frame, text="Only active", variable=self.active_only_var, command=self.on_active_only_toggle)
        self.active_only_check.pack(side=tk.LEFT, padx=5)

        target_label = tk.Label(config_frame, text="Target Filter:")
        target_label.pack(side=tk.LEFT, padx=(10, 0))
        self.target_filter_var = tk.StringVar()
        self.target_filter_entry = tk.Entry(config_frame, textvariable=self.target_filter_var, width=10, relief=tk.RIDGE, borderwidth=2)
        self.target_filter_entry.pack(side=tk.LEFT)

        # Search Filter Label and Entry
        search_label = tk.Label(config_frame, text="Search filter:")
        search_label.pack(side=tk.LEFT, padx=(10, 0))
        self.search_filter_entry = tk.Entry(config_frame, textvariable=self.filter_term, width=15, relief=tk.RIDGE, borderwidth=2)
        self.search_filter_entry.pack(side=tk.LEFT)
        self.search_filter_entry.bind("<Return>", self.on_search_filter_change)
        self.target_filter_entry.bind("<Return>", self.on_target_filter_change)

        # UTC Time Label
        self.utc_time_label = tk.Label(config_frame, text="", font=("Arial", 10, "bold"))
        self.utc_time_label.pack(side=tk.RIGHT, padx=(0, 5)) # Pack to the right with some padding

        list_frame = tk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Header Listbox for horizontal scrolling
        self.header_listbox = Listbox(list_frame, font=("Courier", 10), height=1, exportselection=False)
        self.header_listbox.pack(fill=tk.X)

        self.separator_label = tk.Label(list_frame, text="================================================================================", font=("Courier", 10), anchor="w")
        self.separator_label.pack(fill=tk.X)

        # Frame for main listbox and its scrollbars
        main_list_frame = tk.Frame(list_frame)
        main_list_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = Listbox(main_list_frame, font=("Courier", 10), selectmode=tk.NONE)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind("<Button-1>", self.on_listbox_click)

        # Vertical Scrollbar
        v_scrollbar = Scrollbar(main_list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=v_scrollbar.set)

        # Horizontal Scrollbar
        self.h_scrollbar = Scrollbar(list_frame, orient=tk.HORIZONTAL)
        self.h_scrollbar.pack(fill=tk.X)

        # Connect horizontal scrollbar to both listboxes
        self.listbox.config(xscrollcommand=self.h_scrollbar.set)
        self.header_listbox.config(xscrollcommand=self.h_scrollbar.set)
        self.h_scrollbar.config(command=self.on_horizontal_scroll)

    def show_about_dialog(self):
        about_dialog = tk.Toplevel(self.master)
        about_dialog.title("About eibi_tuner")
        about_dialog.transient(self.master) # Make dialog transient for the main window
        about_dialog.grab_set() # Make dialog modal

        tk.Label(about_dialog, text="eibi_tuner v2.0", font=("Arial", 12, "bold")).pack(pady=10)
        tk.Label(about_dialog, text="Created by Peter Betz (DD2ZG) with support of Gemini 2.5").pack(pady=5)

        ok_button = tk.Button(about_dialog, text="OK", command=about_dialog.destroy)
        ok_button.pack(pady=10)

        # Center the dialog
        about_dialog.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (about_dialog.winfo_width() // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (about_dialog.winfo_height() // 2)
        about_dialog.geometry(f" + {x} + {y}")

        self.master.wait_window(about_dialog) # Wait for dialog to close

    def on_horizontal_scroll(self, *args):
        self.listbox.xview(*args)
        self.header_listbox.xview(*args)

    def update_utc_time(self):
        now_utc = datetime.now(timezone.utc)
        self.utc_time_label.config(text=f"UTC: {now_utc.strftime('%H:%M:%S')}")
        self.master.after(1000, self.update_utc_time) # Update every 1 second

    def _is_time_valid(self, time_range_str, current_utc_time):
        if not time_range_str or time_range_str == "0000-2400":
            return True

        try:
            start_str, end_str = time_range_str.split('-')
            start_hour = int(start_str[:2])
            start_minute = int(start_str[2:])
            end_hour = int(end_str[:2])
            end_minute = int(end_str[2:])

            current_minutes = current_utc_time.hour * 60 + current_utc_time.minute
            start_minutes = start_hour * 60 + start_minute
            end_minutes = end_hour * 60 + end_minute

            if start_minutes <= end_minutes:
                return start_minutes <= current_minutes < end_minutes
            else: # Overnight schedule, e.g., 2300-0100
                return current_minutes >= start_minutes or current_minutes < end_minutes
        except (ValueError, IndexError):
            return False

    def _is_day_valid(self, days_str, current_utc_weekday):
        if not days_str:
            return True # Empty days string means all days

        day_map = {
            "Mo": 0, "Tu": 1, "We": 2, "Th": 3, "Fr": 4, "Sa": 5, "Su": 6,
            "1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6
        }

        valid_weekdays = set()

        # Handle ranges like We-Mo or 1-7
        if '-' in days_str:
            start_day_str, end_day_str = days_str.split('-')
            start_day_int = day_map.get(start_day_str)
            end_day_int = day_map.get(end_day_str)

            if start_day_int is not None and end_day_int is not None:
                if start_day_int <= end_day_int:
                    for i in range(start_day_int, end_day_int + 1):
                        valid_weekdays.add(i)
                else: # Overnight range, e.g., Friday to Monday
                    for i in range(start_day_int, 7):
                        valid_weekdays.add(i)
                    for i in range(0, end_day_int + 1):
                        valid_weekdays.add(i)
        else: # Handles single day abbreviations, or sequences like '1234567' or '.2.4.6.'
            found_digit_day = False
            for char in days_str:
                if char.isdigit():
                    day_int = day_map.get(char)
                    if day_int is not None:
                        valid_weekdays.add(day_int)
                        found_digit_day = True

            # If no digit days were found, try to parse the whole string as an abbreviation
            if not found_digit_day:
                day_int = day_map.get(days_str.strip())
                if day_int is not None:
                    valid_weekdays.add(day_int)

        return current_utc_weekday in valid_weekdays

    def create_menu(self):
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        self.menubar = menubar # Store reference to menubar

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open EIBI .csv file...", command=self.open_eibi_file_dialog)
        file_menu.add_command(label="Open ILG .csv file...", command=self.open_ilg_file_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.master.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        about_menu = tk.Menu(menubar, tearoff=0)
        about_menu.add_command(label="About", command=self.show_about_dialog)
        menubar.add_cascade(label="About", menu=about_menu)


        


    def open_eibi_file_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Open EIBI file",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
        )
        if filepath:
            self._load_eibi_file_csv(filepath)

    def _load_eibi_file_csv(self, filepath):
        # Reset last-update state to force a refresh
        self.last_flrig_freq_hz = None
        self.last_update_minute = None

        self.current_filepath = filepath
        self.current_file_type = "EIBI"
        self.all_data_lines.clear()
        self.eibi_column_names.clear()

        now_utc = datetime.now(timezone.utc)
        current_utc_weekday = now_utc.weekday()

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            if not lines:
                print("Error: EIBI CSV file is empty.")
                return

            # Parse header line
            header_line = lines[0].strip()
            raw_column_names = header_line.split(';')
            self.eibi_column_names = [col.split(':')[0].strip() for col in raw_column_names if col.strip()]
            
            if not self.eibi_column_names:
                print("Error: Could not parse header line in EIBI CSV file.")
                return

            # Process data lines
            for line in lines[1:]: # Skip header line
                stripped_line = line.strip()
                parts = stripped_line.split(';')
                
                if not parts or not parts[0].replace('.', '', 1).isdigit(): # Check if the first part is a number (frequency)
                    continue # Skip lines that don't start with a frequency

                try:
                    data_item = {}
                    for j, col_name in enumerate(self.eibi_column_names):
                        if j < len(parts):
                            data_item[col_name] = parts[j].strip()
                        else:
                            data_item[col_name] = ""
                    
                    # Convert frequency to float
                    data_item["kHz"] = float(data_item["kHz"])

                    if self.active_only_var.get():
                        time_range_str = data_item.get("Time(UTC)", "")
                        days_str = data_item.get("Days", "")
                        time_valid = self._is_time_valid(time_range_str, now_utc)
                        day_valid = self._is_day_valid(days_str, current_utc_weekday)
                        if not time_valid or not day_valid:
                            continue

                    target_filter = self.target_filter_var.get()
                    if target_filter:
                        target_str = data_item.get("Target", "")
                        if target_filter.lower() not in target_str.lower():
                            continue

                    self.all_data_lines.append(data_item)
                except (ValueError, KeyError) as e:
                    print(f"Skipping EIBI line due to parsing error: {e} in line: {stripped_line}")
                    continue
        
        # Calculate maximum column widths for EIBI data
        self.eibi_column_widths = {col: len(col) for col in self.eibi_column_names}
        for data_item in self.all_data_lines:
            for col_name, value in data_item.items():
                if col_name == "kHz":
                    formatted_len = len(f"{value:<.2f}") # Consider 2 decimal places
                else:
                    formatted_len = len(str(value))
                if col_name in self.eibi_column_widths:
                    self.eibi_column_widths[col_name] = max(self.eibi_column_widths.get(col_name, 0), formatted_len)
        
        # Add a small padding to each column width
        for col_name in self.eibi_column_widths:
            self.eibi_column_widths[col_name] += 2 # 2 spaces padding

        self.update_header_and_listbox_display()
        self.update_view_mode_display()

    def open_ilg_file_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Open ILG File",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
        )
        if filepath:
            self.load_ilg_file(filepath)

    def load_ilg_file(self, filepath):
        # Reset last-update state to force a refresh
        self.last_flrig_freq_hz = None
        self.last_update_minute = None

        self.current_filepath = filepath
        self.current_file_type = "ILG"
        self.all_data_lines.clear()
        self.ilg_column_names.clear()

        now_utc = datetime.now(timezone.utc)
        current_utc_weekday = now_utc.weekday()

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            header_found = False
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                if "FREQkhz" in stripped_line and not stripped_line.startswith(('##', '###')):
                    # This is likely the header line
                    raw_column_names = stripped_line.split(';')
                    self.ilg_column_names = [col.replace('##', '').replace('###', '').strip() for col in raw_column_names]
                    # Remove empty strings from column names
                    self.ilg_column_names = [col for col in self.ilg_column_names if col]
                    header_found = True
                    # Start processing data from the next line
                    data_start_index = i + 1
                    break
            
            if not header_found:
                print("Error: Could not find a suitable header line in the ILG file.")
                return

            cols_to_exclude = [
                "24 HOURS TIMES BY LINES IN 30 MINUTE UTC STEPS", 
                "AZI", 
                "REMARKS/COMMENT", 
                "M", 
                "CIRAFZONES - RECEPTION ZONES", 
                "COUNTRY OF TRANSM.", 
                "POSITION: LONGI,LATI", 
                "B", "S", "YY,", 
                "CALL SIGN - NETWORK IDENTIFICATION", 
                "Start", "Stop",
                "TARGET AREA MATRIX",
                "STN",
                "LONGI",
                "LATI"
            ]

            for line in lines[data_start_index:]:
                parts = line.strip().split(';')
                if len(parts) > 0 and parts[0].replace('.', '', 1).isdigit(): # Check if the first part is a number (frequency)
                    try:
                        data_item = {}
                        for j, col_name in enumerate(self.ilg_column_names):
                            if j < len(parts):
                                data_item[col_name] = parts[j].strip()
                            else:
                                data_item[col_name] = ""
                        
                        for col in cols_to_exclude:
                            if col in data_item:
                                del data_item[col]

                        # Convert frequency to float
                        data_item["FREQkhz"] = float(data_item["FREQkhz"])

                        if self.active_only_var.get():
                            time_range_str = data_item.get("TIMES:UTC", "")
                            days_str = data_item.get("1=Sun", "")
                            time_valid = self._is_time_valid(time_range_str, now_utc)
                            day_valid = self._is_day_valid(days_str, current_utc_weekday)
                            if not time_valid or not day_valid:
                                continue

                        target_filter = self.target_filter_var.get()
                        if target_filter:
                            target_str = data_item.get("TARGET", "")
                            if target_filter.lower() not in target_str.lower():
                                continue

                        self.all_data_lines.append(data_item)
                    except (ValueError, KeyError):
                        # Skip lines where frequency cannot be parsed or a key is missing
                        continue
        
        # Filter column names list
        self.ilg_column_names = [col for col in self.ilg_column_names if col not in cols_to_exclude]

        # Calculate maximum column widths for ILG data
        self.ilg_column_widths = {col: len(col) for col in self.ilg_column_names}
        for data_item in self.all_data_lines:
            for col_name, value in data_item.items():
                # Special handling for float formatting of FREQkhz
                if col_name == "FREQkhz":
                    formatted_len = len(f"{value:<.2f}") # Consider 2 decimal places
                else:
                    formatted_len = len(str(value))
                if col_name in self.ilg_column_widths:
                    self.ilg_column_widths[col_name] = max(self.ilg_column_widths.get(col_name, 0), formatted_len)
        
        # Add a small padding to each column width
        for col_name in self.ilg_column_widths:
            self.ilg_column_widths[col_name] += 2 # 2 spaces padding

        self.update_header_and_listbox_display()
        self.update_view_mode_display()

    def on_select(self, event):
        # This method is no longer used as selection is disabled.
        # The functionality is moved to on_listbox_click.
        pass

    def on_listbox_click(self, event):
        self.listbox.selection_clear(0, tk.END) # Clear any selection
        # Get the index of the item clicked
        index = self.listbox.nearest(event.y)
        
        # Adjust index if a temporary line is present above the clicked item
        if self.temp_line_index != -1 and index > self.temp_line_index:
            adjusted_index = index - 1
        else:
            adjusted_index = index
            
        if 0 <= adjusted_index < len(self.displayed_data_items):
            data_item = self.displayed_data_items[adjusted_index]
            frequency_khz = None

            if self.current_file_type == "EIBI":
                frequency_khz = data_item.get("kHz")
            elif self.current_file_type == "ILG":
                frequency_khz = data_item.get("FREQkhz")

            if frequency_khz is not None:
                try:
                    # Ensure frequency_khz is treated as a float before multiplication
                    frequency_hz = int(float(frequency_khz) * 1000)
                    self.set_flrig_frequency(frequency_hz)
                    self.update_view_mode_display(force_update=True)
                except (ValueError, TypeError) as e:
                    print(f"Could not parse frequency from clicked item: {frequency_khz}. Error: {e}")
            else:
                print(f"No frequency found in clicked item at index {index}.")
        else:
            print(f"Clicked outside valid item range or no items displayed. Index: {index}.")
        return "break"
    def set_flrig_frequency(self, frequency_hz):
        host = self.host_entry.get()
        port = self.port_entry.get()
        try:
            server_url = f"http://{host}:{port}"
            server = xmlrpc.client.ServerProxy(server_url)
            server.main.set_frequency(float(frequency_hz))
            print(f"Frequency set to: {frequency_hz} Hz")
            # server.rig.set_mode("USB")
            # print("Mode set to: USB")
        except ConnectionRefusedError:
            print("Connection to FLRIG refused. Is FLRIG running?")
        except Exception as e:
            print(f"An error occurred while setting frequency: {e}")

    def get_flrig_frequency(self):
        host = self.host_entry.get()
        port = self.port_entry.get()
        try:
            server_url = f"http://{host}:{port}"
            server = xmlrpc.client.ServerProxy(server_url)
            frequency_raw = server.rig.get_vfo()
            try:
                frequency_hz = float(frequency_raw)
                return frequency_hz
            except ValueError:
                print(f"Could not convert FLRIG frequency '{frequency_raw}' to a number.")
                return None
        except ConnectionRefusedError:
            print("Connection to FLRIG refused. Is FLRIG running?")
            return None
            print(f"An error occurred while getting frequency: {e}")
            return None

    def update_view_mode_display(self, force_update=False):
        now_utc = datetime.now(timezone.utc)
        current_flrig_freq_hz = self.get_flrig_frequency()

        freq_changed = True
        if current_flrig_freq_hz is not None and self.last_flrig_freq_hz is not None:
            if abs(current_flrig_freq_hz - self.last_flrig_freq_hz) < 10: # 10 Hz tolerance
                freq_changed = False
        
        minute_changed = now_utc.minute != self.last_update_minute

        # If nothing significant changed, and not forced, just reschedule and exit
        if not force_update and not freq_changed and not minute_changed:
            if self.mode == "View":
                self.after_id = self.master.after(1000, self.update_view_mode_display)
            return

        # Update last known values
        self.last_update_minute = now_utc.minute
        if current_flrig_freq_hz is not None:
            self.last_flrig_freq_hz = current_flrig_freq_hz

        # Check if a temporary line was present and needs to be removed
        temp_line_was_present = (self.temp_line_index != -1)
        if temp_line_was_present:
            # If a temp line was present, and we are now going to highlight actual matches,
            # or if the target frequency changed, we need to rebuild the listbox
            # to remove the temp line and ensure indices are correct.
            # We will clear temp_line_index here, and it will be re-added later if needed.
            self.temp_line_index = -1
            self.update_listbox_display() # Rebuilds listbox and displayed_data_items
            # After rebuilding, the previous highlights are no longer valid, so clear them
            self.previous_highlights.clear()

        # Revert previous highlights (only if listbox wasn't rebuilt)
        if not temp_line_was_present: # Only revert if we didn't just rebuild the listbox
            for index, original_bg, original_fg in self.previous_highlights:
                if 0 <= index < self.listbox.size():
                    self.listbox.itemconfig(index, {'bg': original_bg, 'fg': original_fg})
            self.previous_highlights.clear()

        target_freq_khz = None
        if current_flrig_freq_hz is not None:
            target_freq_khz = current_flrig_freq_hz / 1000

        current_utc_weekday = now_utc.weekday()
        exact_match_found = False
        first_exact_match_index = -1
        closest_freq_index = -1
        closest_freq_diff = float('inf')

        default_listbox_bg = self.listbox.cget("bg")
        default_listbox_fg = self.listbox.cget("fg")

        new_highlights = [] # To store highlights for the current cycle

        for i, data_item in enumerate(self.displayed_data_items):
            list_freq_khz = None
            if self.current_file_type == "EIBI":
                list_freq_khz = data_item.get("kHz")
            elif self.current_file_type == "ILG":
                list_freq_khz = data_item.get("FREQkhz")
            
            if target_freq_khz is not None and list_freq_khz is not None:
                diff = abs(list_freq_khz - target_freq_khz)

                if diff < closest_freq_diff:
                    closest_freq_diff = diff
                    closest_freq_index = i

                if diff < 0.01: # Frequency matches
                    exact_match_found = True
                    if first_exact_match_index == -1:
                        first_exact_match_index = i

                    # Always store default colors for reversion
                    new_highlights.append((i, default_listbox_bg, default_listbox_fg))

                    # Default highlight for frequency match is grey
                    self.listbox.itemconfig(i, {'bg': 'dark grey', 'fg': 'white'})

                    # Now, check for time/day match to override with yellow
                    is_active = True
                    if self.current_file_type == "EIBI":
                        time_range_str = data_item.get("Time(UTC)", "")
                        days_str = data_item.get("Days", "")
                        time_valid = self._is_time_valid(time_range_str, now_utc)
                        day_valid = self._is_day_valid(days_str, current_utc_weekday)
                        if not time_valid or not day_valid:
                            is_active = False
                    elif self.current_file_type == "ILG":
                        time_range_str = data_item.get("TIMES:UTC", "")
                        days_str = data_item.get("1=Sun", "")
                        time_valid = self._is_time_valid(time_range_str, now_utc)
                        day_valid = self._is_day_valid(days_str, current_utc_weekday)
                        if not time_valid or not day_valid:
                            is_active = False
                    
                    if is_active:
                        self.listbox.itemconfig(i, {'bg': 'yellow', 'fg': 'black'})
        
        self.previous_highlights = new_highlights # Store highlights for next cycle

        item_to_center_index = -1

        if target_freq_khz is not None and not exact_match_found:
            insert_index = 0
            if closest_freq_index != -1 and self.displayed_data_items:
                for i, data_item in enumerate(self.displayed_data_items):
                    list_freq_khz = None
                    if self.current_file_type == "EIBI":
                        list_freq_khz = data_item.get("kHz")
                    elif self.current_file_type == "ILG":
                        list_freq_khz = data_item.get("FREQkhz")
                    if list_freq_khz is not None and list_freq_khz > target_freq_khz:
                        insert_index = i
                        break
                    insert_index = i + 1

            self.listbox.insert(insert_index, f"---- {target_freq_khz:.2f}")
            self.listbox.itemconfig(insert_index, {'bg': 'black', 'fg': 'yellow'})
            self.temp_line_index = insert_index
            item_to_center_index = insert_index
        elif target_freq_khz is not None:
            item_to_center_index = first_exact_match_index

        if item_to_center_index != -1:
            self.listbox.see(item_to_center_index)
            first_visible_idx = int(self.listbox.yview()[0] * self.listbox.size())
            last_visible_idx = int(self.listbox.yview()[1] * self.listbox.size())
            visible_lines = last_visible_idx - first_visible_idx
            scroll_offset = item_to_center_index - first_visible_idx - (visible_lines // 2)
            self.listbox.yview_scroll(scroll_offset, 'units')
        elif target_freq_khz is not None:
            print(f"No relevant frequency found for centering {target_freq_khz} kHz.")

        if self.mode == "View":
            self.after_id = self.master.after(1000, self.update_view_mode_display)











    def on_search_filter_change(self, event):
        # The filter_term is already updated via textvariable binding
        self.update_listbox_display()
        self.update_view_mode_display(force_update=True)

    def on_active_only_toggle(self):
        if hasattr(self, 'current_filepath') and self.current_filepath:
            if self.current_file_type == "EIBI":
                self._load_eibi_file_csv(self.current_filepath)
            elif self.current_file_type == "ILG":
                self.load_ilg_file(self.current_filepath)

    def on_target_filter_change(self, event):
        if hasattr(self, 'current_filepath') and self.current_filepath:
            if self.current_file_type == "EIBI":
                self._load_eibi_file_csv(self.current_filepath)
            elif self.current_file_type == "ILG":
                self.load_ilg_file(self.current_filepath)

    def update_listbox_display(self):
        self.listbox.delete(0, tk.END)
        self.displayed_data_items.clear() # Clear the list of displayed data items

        for data_item in self.all_data_lines:
            display_line = ""
            if self.current_file_type == "EIBI":
                # Format EIBI data to display all columns using calculated widths
                formatted_parts = []
                for col_name in self.eibi_column_names:
                    value = data_item.get(col_name, "")
                    width = self.eibi_column_widths.get(col_name, 15) # Default to 15 if width not found
                    if col_name == "kHz":
                        formatted_parts.append(f"{value:<{width}.2f}") # Format frequency specifically
                    else:
                        formatted_parts.append(f"{str(value):<{width}}")
                display_line = "".join(formatted_parts)
            elif self.current_file_type == "ILG":
                # Format ILG data to display all columns using calculated widths
                formatted_parts = []
                for col_name in self.ilg_column_names:
                    value = data_item.get(col_name, "")
                    width = self.ilg_column_widths.get(col_name, 15) # Default to 15 if width not found
                    if col_name == "FREQkhz":
                        formatted_parts.append(f"{value:<{width}.2f}") # Format frequency specifically
                    else:
                        formatted_parts.append(f"{str(value):<{width}}")
                display_line = "".join(formatted_parts)
            
            filter_value = self.filter_term.get().lower()
            should_display = False

            if not filter_value: # No filter, display all
                should_display = True
            elif self.current_file_type == "EIBI":
                if filter_value in display_line.lower():
                    should_display = True
            elif self.current_file_type == "ILG":
                # Search within all values of the data_item for ILG
                for value in data_item.values():
                    if filter_value in str(value).lower():
                        should_display = True
                        break
            
            if should_display:
                self.displayed_data_items.append(data_item) # Store the actual data_item
                self.listbox.insert(tk.END, display_line)

    def update_header_and_listbox_display(self):
        self.header_listbox.delete(0, tk.END) # Clear previous header
        header_text = ""
        header_width = 0

        if self.current_file_type == "EIBI":
            # Dynamically create header from eibi_column_names using calculated widths
            header_parts = []
            for col_name in self.eibi_column_names:
                width = self.eibi_column_widths.get(col_name, len(col_name) + 2) # Default to name length + padding
                header_parts.append(f"{col_name:<{width}}")
            header_text = "".join(header_parts)
            header_width = len(header_text)
        elif self.current_file_type == "ILG":
            # Dynamically create header from ilg_column_names using calculated widths
            header_parts = []
            for col_name in self.ilg_column_names:
                width = self.ilg_column_widths.get(col_name, len(col_name) + 2) # Default to name length + padding
                header_parts.append(f"{col_name:<{width}}")
            header_text = "".join(header_parts)
            header_width = len(header_text)
        
        if header_text:
            self.header_listbox.insert(tk.END, header_text)

        self.separator_label.config(text="=" * header_width)
        self.update_listbox_display()

    def show_about_dialog(self):
        about_dialog = tk.Toplevel(self.master)
        about_dialog.title("About eibi_tuner")
        about_dialog.transient(self.master) # Make dialog transient for the main window
        about_dialog.grab_set() # Make dialog modal

        tk.Label(about_dialog, text="eibi_tuner v2.0", font=("Arial", 12, "bold")).pack(pady=10)
        tk.Label(about_dialog, text="Created by Peter Betz (DD2ZG) with support of Gemini 2.5").pack(pady=5)

        ok_button = tk.Button(about_dialog, text="OK", command=about_dialog.destroy)
        ok_button.pack(pady=10)

        # Center the dialog
        about_dialog.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (about_dialog.winfo_width() // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (about_dialog.winfo_height() // 2)
        about_dialog.geometry(f" + {x} + {y}")

        self.master.wait_window(about_dialog) # Wait for dialog to close
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1280x720")
    app = EibiTuner(master=root)
    app.mainloop()
