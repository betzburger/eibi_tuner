
import tkinter as tk
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
        self.filter_term = "" # Initialize filter term
        self.all_eibi_lines = [] # To store all lines from the EIBI file
        self.temp_line_index = -1 # To track the index of the temporary frequency line
        self.create_widgets()
        self.create_menu()
        self.set_mode_view() # Set initial mode to View

    def create_widgets(self):
        config_frame = tk.Frame(self)
        config_frame.pack(fill=tk.X, padx=5, pady=5)

        host_label = tk.Label(config_frame, text="FLRIG Host:")
        host_label.pack(side=tk.LEFT)
        self.host_entry = tk.Entry(config_frame)
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.pack(side=tk.LEFT)

        port_label = tk.Label(config_frame, text="Port:")
        port_label.pack(side=tk.LEFT)
        self.port_entry = tk.Entry(config_frame, width=10)
        self.port_entry.insert(0, "12345")
        self.port_entry.pack(side=tk.LEFT)

        self.mode_label = tk.Label(config_frame, text=f"Mode: {self.mode}", font=("Arial", 10, "bold"))
        self.mode_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        list_frame = tk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.header_label = tk.Label(list_frame, text="kHZ           Time(UTC) Days  ITU Station                Lang. Target   Remarks", font=("Courier", 10), anchor="w")
        self.header_label.pack(fill=tk.X)
        self.separator_label = tk.Label(list_frame, text="================================================================================", font=("Courier", 10), anchor="w")
        self.separator_label.pack(fill=tk.X)

        self.listbox = Listbox(list_frame, font=("Courier", 10))
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        scrollbar = Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

    def create_menu(self):
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        self.menubar = menubar # Store reference to menubar

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open EIBI File...", command=self.load_eibi_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.master.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        self.mode_menu = tk.Menu(menubar, tearoff=0)
        self.mode_menu.add_command(label="View", command=self.set_mode_view)
        self.mode_menu.add_command(label="Send", command=self.set_mode_send)
        menubar.add_cascade(label="List", menu=self.mode_menu)
        
        # Create a separate menu for Search
        self.search_menu = tk.Menu(menubar, tearoff=0)
        self.search_menu.add_command(label="Search", command=self.open_search_dialog)
        menubar.add_cascade(label="Search", menu=self.search_menu)
        
        # Set initial state of Search menu item
        self.search_menu.entryconfig("Search", state=tk.NORMAL if self.mode == "Send" else tk.DISABLED)

    def load_eibi_file(self):
        filepath = filedialog.askopenfilename(
            title="Open EIBI File",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if not filepath:
            return

        self.all_eibi_lines.clear()
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if len(line) > 60 and line[0].isdigit(): # Only consider data lines
                    self.all_eibi_lines.append(line.strip())
        self.update_listbox_display()

    def on_select(self, event):
        selection = event.widget.curselection()
        if not selection:
            return

        selected_item = event.widget.get(selection[0])
        frequency_khz_str = selected_item.split()[0]

        if self.mode == "Send":
            try:
                frequency_khz = float(frequency_khz_str)
                frequency_hz = int(frequency_khz * 1000)
                self.set_flrig_frequency(frequency_hz)
            except (ValueError, IndexError):
                print(f"Could not parse frequency: {frequency_khz_str}")
            except Exception as e:
                print(f"An error occurred: {e}")

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

    def update_view_mode_display(self):
        current_flrig_freq_hz = self.get_flrig_frequency()
        if current_flrig_freq_hz is None:
            if self.mode == "View": # Reschedule only if still in View mode
                self.after_id = self.master.after(1000, self.update_view_mode_display) # Check every 1 second
            return

        target_freq_khz = current_flrig_freq_hz / 1000

        # Remove previous temporary line if it exists
        if self.temp_line_index != -1:
            try:
                self.listbox.delete(self.temp_line_index)
            except tk.TclError: # Handle case where index might be invalid (e.g., listbox reloaded)
                pass
            self.temp_line_index = -1

        # Clear all highlighting
        for i in range(self.listbox.size()):
            self.listbox.itemconfig(i, {'bg': 'black', 'fg': 'white'})

        exact_match_found = False
        first_exact_match_index = -1
        closest_freq_index = -1
        closest_freq_diff = float('inf')

        # Iterate through current listbox items to find matches and closest frequency
        current_listbox_items = []
        for i in range(self.listbox.size()):
            current_listbox_items.append(self.listbox.get(i))

        for i, line in enumerate(current_listbox_items):
            try:
                list_freq_khz = float(line.split()[0])
                diff = abs(list_freq_khz - target_freq_khz)

                # Find the closest frequency (for centering)
                if diff < closest_freq_diff:
                    closest_freq_diff = diff
                    closest_freq_index = i

                # Check for exact matches (for highlighting)
                if diff < 0.01: # Tolerance for exact match (e.g., 10 Hz)
                    exact_match_found = True
                    if first_exact_match_index == -1:
                        first_exact_match_index = i
                    self.listbox.itemconfig(i, {'bg': 'yellow', 'fg': 'black'})

            except (ValueError, IndexError):
                continue

        item_to_center_index = -1

        if not exact_match_found:
            # Insert temporary line
            insert_index = 0
            if closest_freq_index != -1 and current_listbox_items:
                # Determine insertion point: find the first item greater than target_freq_khz
                for i, line in enumerate(current_listbox_items):
                    try:
                        list_freq_khz = float(line.split()[0])
                        if list_freq_khz > target_freq_khz:
                            insert_index = i
                            break
                        insert_index = i + 1 # If no greater frequency, insert at end
                    except (ValueError, IndexError):
                        continue

            self.listbox.insert(insert_index, f"---- {target_freq_khz:.2f}")
            self.listbox.itemconfig(insert_index, {'bg': 'black', 'fg': 'yellow'})
            self.temp_line_index = insert_index
            item_to_center_index = insert_index
        else:
            item_to_center_index = first_exact_match_index

        # Centering logic
        if item_to_center_index != -1:
            self.listbox.see(item_to_center_index) # Bring the item into view
            
            first_visible_idx = int(self.listbox.yview()[0] * self.listbox.size())
            last_visible_idx = int(self.listbox.yview()[1] * self.listbox.size())
            visible_lines = last_visible_idx - first_visible_idx
            
            scroll_offset = item_to_center_index - first_visible_idx - (visible_lines // 2)
            self.listbox.yview_scroll(scroll_offset, 'units')
        else:
            print(f"No relevant frequency found for centering {target_freq_khz} kHz.")

        if self.mode == "View": # Reschedule only if still in View mode
            self.after_id = self.master.after(1000, self.update_view_mode_display) # Check every 1 second

    def set_mode_view(self):
        self.mode = "View"
        self.mode_label.config(text=f"Mode: {self.mode}")
        self.search_menu.entryconfig("Search", state=tk.DISABLED)
        
        # Clear filter when entering View mode
        self.filter_term = ""
        self.update_listbox_display()

        print("Mode set to: View")
        self.update_view_mode_display()

    def set_mode_send(self):
        self.mode = "Send"
        self.mode_label.config(text=f"Mode: {self.mode}")
        self.search_menu.entryconfig("Search", state=tk.NORMAL)
        print("Mode set to: Send")
        if self.after_id:
            self.master.after_cancel(self.after_id)
            self.after_id = None
        
        # Remove temporary line if it exists when switching to Send mode
        if self.temp_line_index != -1:
            try:
                self.listbox.delete(self.temp_line_index)
            except tk.TclError:
                pass
            self.temp_line_index = -1

        # Clear any highlighting when switching to Send mode
        for i in range(self.listbox.size()):
            self.listbox.itemconfig(i, {'bg': 'black', 'fg': 'white'})

    def open_search_dialog(self):
        search_dialog = tk.Toplevel(self.master)
        search_dialog.title("Search Filter")
        search_dialog.transient(self.master) # Make dialog transient for the main window
        search_dialog.grab_set() # Make dialog modal

        tk.Label(search_dialog, text="Enter search term:").pack(padx=10, pady=5)
        self.search_entry = tk.Entry(search_dialog, width=40)
        self.search_entry.insert(0, self.filter_term) # Show current filter
        self.search_entry.pack(padx=10, pady=5)
        self.search_entry.focus_set() # Automatically activate input field
        self.search_entry.bind("<Return>", lambda event: self.apply_filter(self.search_entry.get(), search_dialog))

        button_frame = tk.Frame(search_dialog)
        button_frame.pack(pady=5)

        tk.Button(button_frame, text="Apply Filter", command=lambda: self.apply_filter(self.search_entry.get(), search_dialog)).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Clear Filter", command=lambda: self.clear_filter(search_dialog)).pack(side=tk.LEFT, padx=5)

        search_dialog.protocol("WM_DELETE_WINDOW", lambda: self.on_dialog_close(search_dialog)) # Handle window close
        self.master.wait_window(search_dialog) # Wait for dialog to close

    def apply_filter(self, term, dialog):
        self.filter_term = term.lower() # Store filter term in lowercase for case-insensitive search
        self.update_listbox_display() # Update the listbox with filtered results
        dialog.destroy()

    def clear_filter(self, dialog):
        self.filter_term = ""
        self.update_listbox_display() # Update the listbox with all results
        dialog.destroy()

    def on_dialog_close(self, dialog):
        dialog.destroy()

    def update_listbox_display(self):
        self.listbox.delete(0, tk.END)
        for line in self.all_eibi_lines:
            if self.filter_term in line.lower() or not self.filter_term:
                self.listbox.insert(tk.END, line)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x600")
    app = EibiTuner(master=root)
    app.mainloop()
