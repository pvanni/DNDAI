import re
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as patches
import numpy as np


class PauseAnimation:
    def __init__(self, team1_positions, team2_positions, team1_symbols, team2_symbols, action_texts, action_start_pos, action_end_pos, action_type):

        fig, self.ax = plt.subplots()

        min_val, max_val = 0, 20
        ind_array = np.arange(min_val + 0.5, max_val + 0.5, 1.0)
        self.x, self.y = np.meshgrid(ind_array, ind_array)

        self.action_texts = iter(action_texts)
        self.action_start_pos = iter(action_start_pos)
        self.action_end_pos = iter(action_end_pos)
        self.action_type = iter(action_type)

        self.active_rectangle_pos = []
        self.target_rectangle_pos = []

        self.x = self.x.flatten()
        self.y = self.y.flatten()

        self.team1_color = 'blue'
        self.team2_color = 'red'
        # Draw team 1 positions
        for char_pos, char_symbol in zip(team1_positions, team1_symbols):
            for i, (x_val, y_val) in enumerate(zip(self.x, self.y)):
                if i == char_pos:
                    if char_symbol == 'O1':
                        self.ax.text(x_val + 0.5, y_val + 0.5, char_symbol, va='center', ha='center', fontsize=20, color=self.team1_color)
                        break
                    else:
                        self.ax.text(x_val, y_val, char_symbol, va='center', ha='center', color=self.team1_color)
                        break

        # Draw team 2 positions
        for char_pos, char_symbol in zip(team2_positions, team2_symbols):
            for i, (x_val, y_val) in enumerate(zip(self.x, self.y)):
                if i == char_pos:
                    if char_symbol == 'O2':
                        self.ax.text(x_val + 0.5, y_val + 0.5, char_symbol, va='center', ha='center', fontsize=20, color=self.team2_color)
                        break
                    else:
                        self.ax.text(x_val, y_val, char_symbol, va='center', ha='center', color=self.team2_color)
                        break

        self.ax.set_xlim(min_val, max_val)
        self.ax.set_ylim(min_val, max_val)
        self.ax.set_xticks(np.arange(max_val))
        self.ax.set_yticks(np.arange(max_val))
        self.ax.grid()

        #self.ax.set_title('Click to pause/resume the animation')

        self.animation = animation.FuncAnimation(
            fig, self.update, interval=50, frames=len(action_texts)-1, repeat=True)
        self.paused = False

        #plt.show()
        plt.close()

        FFwriter = animation.FFMpegWriter(fps=1)
        self.animation.save('match.mp4', writer=FFwriter)

        #fig.canvas.mpl_connect('button_press_event', self.toggle_pause)

    def toggle_pause(self, *args, **kwargs):
        if self.paused:
            self.animation.resume()
        else:
            self.animation.pause()
        self.paused = not self.paused

    def update(self, i):

        """
        if len(self.ax.texts) > 0:
            #print(self.ax.texts[0].get_position()[0])
            self.ax.texts[0].remove()
        """
        # Get the next action
        next_action_text = next(self.action_texts)
        next_action_start_pos = next(self.action_start_pos)
        next_action_end_pos = next(self.action_end_pos)
        next_action_type = next(self.action_type)

        # Remove all rectangles
        for i in self.active_rectangle_pos:
            for patch_i in range(len(self.ax.patches)):
                if self.ax.patches[patch_i].get_xy() == i:
                    self.ax.patches[patch_i].remove()
                    break

        self.active_rectangle_pos = []

        # Remove target rectangle
        for i in self.target_rectangle_pos:
            for patch_i in range(len(self.ax.patches)):
                if self.ax.patches[patch_i].get_xy() == i:
                    self.ax.patches[patch_i].remove()
                    break

        self.target_rectangle_pos = []

        if next_action_type == 'Move':
            # Find the old symbol and draw it in the new spot
            symbol = 0
            for i, (x_val, y_val) in enumerate(zip(self.x, self.y)):
                if i == next_action_start_pos:
                    for text_i in range(len(self.ax.texts)):
                        if self.ax.texts[text_i].get_text() in ['O1', 'O2']:
                            if self.ax.texts[text_i].get_position() == (x_val + 0.5, y_val + 0.5):
                                symbol = self.ax.texts[text_i].get_text()
                                self.ax.texts[text_i].remove()
                                break
                        else:
                            if self.ax.texts[text_i].get_position() == (x_val, y_val):
                                symbol = self.ax.texts[text_i].get_text()
                                self.ax.texts[text_i].remove()
                                break

                    if symbol != 0:
                        break
            if symbol != 0:
                # Draw the new position
                for i, (x_val, y_val) in enumerate(zip(self.x, self.y)):
                    if i == next_action_end_pos:
                        if '1' in symbol:
                            color = self.team1_color
                        else:
                            color = self.team2_color

                        if symbol in ['O1', 'O2']:
                            # Active rectangle
                            rect = patches.Rectangle(xy=(x_val-0.5, y_val-0.5), width=2, height=2, color='green', linewidth=5, fill=False)
                            self.active_rectangle_pos.append((x_val - 0.5, y_val - 0.5))
                            self.ax.add_patch(rect)
                            self.ax.text(x_val+0.5, y_val+0.5, symbol, va='center', ha='center', color=color, fontsize=20)
                            break
                        else:
                            rect = patches.Rectangle(xy=(x_val-0.5, y_val-0.5), width=1, height=1, color='green', linewidth=5, fill=False)
                            self.active_rectangle_pos.append((x_val - 0.5, y_val - 0.5))
                            self.ax.add_patch(rect)
                            self.ax.text(x_val, y_val, symbol, va='center', ha='center', color=color)
                            break

        if 'attacked' in next_action_text or 'cast spell' in next_action_text:
            # Draw the new position
            for i, (x_val, y_val) in enumerate(zip(self.x, self.y)):
                if i == next_action_end_pos:
                    # Active rectangle
                    rect = patches.Rectangle(xy=(x_val - 0.5, y_val - 0.5), width=1, height=1, color='orange',
                                             linewidth=5, fill=False)
                    self.target_rectangle_pos.append((x_val - 0.5, y_val - 0.5))
                    self.ax.add_patch(rect)

                if not 'Moving' in next_action_text:
                    if i == next_action_start_pos:
                        # Active rectangle
                        already_drawn = False
                        for patch_i in range(len(self.ax.patches)):
                            if self.ax.patches[patch_i].get_xy() == next_action_start_pos:
                                already_drawn = True

                        if not already_drawn:
                            rect = patches.Rectangle(xy=(x_val - 0.5, y_val - 0.5), width=1, height=1, color='green',
                                                     linewidth=5, fill=False)
                            self.active_rectangle_pos.append((x_val - 0.5, y_val - 0.5))
                            self.ax.add_patch(rect)


        if next_action_type == 'End' or next_action_type == 'Dodge':
            for i, (x_val, y_val) in enumerate(zip(self.x, self.y)):
                if i == next_action_end_pos:
                    # Active rectangle
                    rect = patches.Rectangle(xy=(x_val - 0.5, y_val - 0.5), width=1, height=1,
                                             color='green', linewidth=5, fill=False)
                    self.active_rectangle_pos.append((x_val - 0.5, y_val - 0.5))
                    self.ax.add_patch(rect)
                    break

        if next_action_type == 'End' or next_action_type == 'Dodge':
            for i, (x_val, y_val) in enumerate(zip(self.x, self.y)):
                if i == next_action_end_pos:
                    # Active rectangle
                    rect = patches.Rectangle(xy=(x_val - 0.5, y_val - 0.5), width=1, height=1,
                                             color='green', linewidth=5, fill=False)
                    self.active_rectangle_pos.append((x_val - 0.5, y_val - 0.5))
                    self.ax.add_patch(rect)
                    break

        # If moving as part of the attack action, move the marker
        if 'Moving' in next_action_text:
            moving_index = next_action_text.find('Moving')
            linebreak_index = next_action_text[moving_index:].find('\n')
            sentence = next_action_text[moving_index:][:linebreak_index]
            sen_num = [int(s) for s in re.findall(r'\b\d+\b', sentence)]
            # Find the old symbol and draw it in the new spot
            symbol = 0
            for i, (x_val, y_val) in enumerate(zip(self.x, self.y)):
                if i == next_action_start_pos:
                    for text_i in range(len(self.ax.texts)):
                        if self.ax.texts[text_i].get_text() in ['O1', 'O2']:
                            if self.ax.texts[text_i].get_position() == (x_val + 0.5, y_val + 0.5):
                                rect = patches.Rectangle(xy=(x_val - 0.5, y_val - 0.5), width=2, height=2,
                                                         color='green', linewidth=5, fill=False)
                                self.active_rectangle_pos.append((x_val - 0.5, y_val - 0.5))
                                self.ax.add_patch(rect)
                                symbol = self.ax.texts[text_i].get_text()
                                self.ax.texts[text_i].remove()
                                break
                        else:
                            if self.ax.texts[text_i].get_position() == (x_val, y_val):
                                rect = patches.Rectangle(xy=(x_val - 0.5, y_val - 0.5), width=1, height=1,
                                                         color='green', linewidth=5, fill=False)
                                self.active_rectangle_pos.append((x_val - 0.5, y_val - 0.5))
                                self.ax.add_patch(rect)
                                symbol = self.ax.texts[text_i].get_text()
                                self.ax.texts[text_i].remove()
                                break

                    if symbol != 0:
                        break
            if symbol != 0:
                # Draw the new position
                for i, (x_val, y_val) in enumerate(zip(self.x, self.y)):
                    if i == sen_num[1]:
                        if '1' in symbol:
                            color = self.team1_color
                        else:
                            color = self.team2_color
                        if symbol in ['O1', 'O2']:
                            rect = patches.Rectangle(xy=(x_val - 0.5, y_val - 0.5), width=2, height=2,
                                                     color='green', linewidth=5, fill=False)
                            self.active_rectangle_pos.append((x_val - 0.5, y_val - 0.5))
                            self.ax.add_patch(rect)
                            self.ax.text(x_val + 0.5, y_val + 0.5, symbol, va='center', ha='center', color=color, fontsize=20)
                            break
                        else:
                            self.ax.text(x_val, y_val, symbol, va='center', ha='center', color=color)
                            rect = patches.Rectangle(xy=(x_val - 0.5, y_val - 0.5), width=1, height=1,
                                                     color='green', linewidth=5, fill=False)
                            self.active_rectangle_pos.append((x_val - 0.5, y_val - 0.5))
                            self.ax.add_patch(rect)
                            break

        # Print action description
        # Remove previous action text
        for text_i in range(len(self.ax.texts)):
            if self.ax.texts[text_i].get_position() == (10.2, 10.2):
                self.ax.texts[text_i].remove()
                break
        self.ax.text(10.2, 10.2, next_action_text, va='center', ha='center')

        # If target dies, remove
        if 'dies' in next_action_text:
            moving_index = next_action_text.find('Character at')
            linebreak_index = next_action_text[moving_index:].find('\n')
            sentence = next_action_text[moving_index:][:linebreak_index]
            sen_num = [int(s) for s in re.findall(r'\b\d+\b', sentence)]

            # If target moved, then its already updated on the picture. Select the picture part
            if 'dies' in next_action_text:
                sen_num[0] = next_action_end_pos

            for i, (x_val, y_val) in enumerate(zip(self.x, self.y)):
                if i == sen_num[0]:
                    for text_i in range(len(self.ax.texts)):
                        if self.ax.texts[text_i].get_position() == (x_val, y_val):
                            print(self.ax.texts[text_i].get_text())
                            self.ax.texts[text_i].remove()
                            break
                        elif self.ax.texts[text_i].get_position() == (x_val+0.5, y_val+0.5):
                            print(self.ax.texts[text_i].get_text())
                            self.ax.texts[text_i].remove()
                            break

        #self.ax.text(next(self.x_iter), next(self.y_iter), 'x', va='center', ha='center')
        return (self.ax,)


# Parse the match log
action_texts = []
action_start_pos = []
action_end_pos = []
action_type = []
team1_positions = [42, 50, 392, 181, 121, 341]
team1_symbols = ['M1', 'M1', 'S1', 'R1', 'R1', 'O1']
team2_positions = [8, 15, 177, 331, 319, 277]
team2_symbols = ['M2', 'M2', 'R2', 'S2', 'R2', 'O2']


with open('logs/log.txt') as file:
    action_count = 1
    action_text = ''

    start_recording = False
    for line in file.readlines():
        if 'Round: ' in line:
            start_recording = False
            action_count += 1
            if action_text != '':
                action_texts.append(action_text)
            action_text = ''

        if f'Action {action_count}:' in line:
            start_recording = True
            numbers = [int(s) for s in re.findall(r'\b\d+\b', line)]

            if 'dodging' in line:
                action_type.append('Dodge')
                action_start_pos.append(numbers[-1])
                action_end_pos.append(numbers[-1])
            else:
                action_end_pos.append(numbers.pop(-1))
                action_start_pos.append(numbers.pop(-1))

            if 'moved' in line:
                action_type.append('Move')
            if 'attacked' in line:
                action_type.append('Attack')
            if 'spell' in line:
                action_type.append('Spell')
            if 'ended turn' in line:
                action_type.append('End')

        if start_recording:
            action_text += line

pa = PauseAnimation(team1_positions, team2_positions, team1_symbols, team2_symbols, action_texts, action_start_pos, action_end_pos, action_type)
#plt.show()