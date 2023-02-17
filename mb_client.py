from mb_gui import *
from message_q import *
import queue

frame_container = tk.Frame(root)
frame_container.pack(fill='x', expand=1, side='top', anchor='n')

frame_hdr = tk.Frame(frame_container, background="black", height=100, pady=10)
frame_hdr.pack(fill='x', expand=1, side='top', anchor='n')
header = GuiHeader(header_frame=frame_hdr)  # populate the header

frame_main = tk.Frame(frame_container, pady=4)
frame_main.pack(fill='both', expand=1, side='top', anchor='n', padx=4)

# Now for the logic

header.set_frequency()
header.set_offset()
header.set_callsign()
header.clock_tick()

main = GuiMain(frame=frame_main)  # populate the main area

main.latest_reload()

main.set_selected_blog('M0PXO')

main.qso_box_reload()

main.blog_list_reload()


root.mainloop()
