To see how this Python 3 script works, please watch the video:

https://youtu.be/T_wUGOk7chA

This Python program, eibi_tuner.py, is a graphical user interface (GUI) application designed to assist shortwave
  listeners and radio amateurs. Its purpose is to load and display frequency lists (EIBI and ILG files in CSV format)
   and interact with the FLRIG software to automatically tune a radio receiver.

  Key Features:

   * Loading Frequency Lists: It can read EIBI (European International Broadcasting Institute) and ILG (International
     Listening Guide) files in CSV format.
   * Data Display: The loaded data is presented in a clear, scrollable list, with column widths adjusted dynamically.
   * Filtering Options:
       * "Only active": Displays only stations that should be active at the current UTC time and weekday.
       * "Target Filter": Filters the list by a specific target area or group.
       * "Search filter": Allows searching for any terms within the displayed data.
   * FLRIG Integration: The program can establish a connection to FLRIG via XML-RPC to set the frequency of a connected
      radio receiver.
   * Dynamic Updates: The display is continuously updated to show the current UTC time and highlight the list based on
     the current frequency of the FLRIG receiver.
   * Highlighting: Entries matching the current FLRIG frequency are highlighted. If a station is active at the current
     time, it is additionally color-coded. A temporary line indicates the current frequency when no exact match is
     found.
   * User-Friendliness: Provides a menu for opening files and an "About" window with program information.

  The program is implemented in Python using the tkinter library for the GUI and xmlrpc.client for communication with
   FLRIG. It was developed to facilitate browsing and tuning into shortwave stations.

<img src="eibi_tuner screenshot.png" alt="" width="800" />
