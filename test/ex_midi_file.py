import numpy as np
import pretty_midi

# Create a PrettyMIDI object
classical_guitar = pretty_midi.PrettyMIDI(initial_tempo=92)

# Create an instrument instance for Classical Guitar (program 24)
guitar_program = 24  # Classical Guitar in General MIDI
guitar = pretty_midi.Instrument(program=guitar_program, name="Classical Guitar")

# Define the pitch ranges for a standard classical guitar
# Standard tuning: E2(40), A2(45), D3(50), G3(55), B3(59), E4(64)
# Playable range approximately from E2(40) to B5(83)

# Create a monophonic melody section (first measure)
start_time = 0.0
notes = [
    # Simple monophonic descending melody
    {"pitch": 64, "start": start_time, "end": start_time + 0.5},  # E4
    {"pitch": 62, "start": start_time + 0.5, "end": start_time + 1.0},  # D4
    {"pitch": 60, "start": start_time + 1.0, "end": start_time + 1.5},  # C4
    {"pitch": 59, "start": start_time + 1.5, "end": start_time + 2.0},  # B3
    {"pitch": 57, "start": start_time + 2.0, "end": start_time + 2.5},  # A3
    {"pitch": 55, "start": start_time + 2.5, "end": start_time + 3.0},  # G3
    {"pitch": 57, "start": start_time + 3.0, "end": start_time + 3.5},  # A3
    {"pitch": 59, "start": start_time + 3.5, "end": start_time + 4.0},  # B3
]

# Add the monophonic notes to the instrument
for note_info in notes:
    note = pretty_midi.Note(
        velocity=70,  # Medium velocity
        pitch=note_info["pitch"],
        start=note_info["start"],
        end=note_info["end"]
    )
    guitar.notes.append(note)

# Create a polyphonic section with arpeggios and chords (second measure)
start_time = 4.0

# Em chord (E minor)
em_chord = [
    {"pitch": 40, "start": start_time, "end": start_time + 2.0},  # E2 (bass)
    {"pitch": 52, "start": start_time, "end": start_time + 2.0},  # E3
    {"pitch": 55, "start": start_time, "end": start_time + 2.0},  # G3
    {"pitch": 59, "start": start_time, "end": start_time + 2.0},  # B3
]

# Am chord (A minor)
am_chord = [
    {"pitch": 45, "start": start_time + 2.0, "end": start_time + 4.0},  # A2 (bass)
    {"pitch": 57, "start": start_time + 2.0, "end": start_time + 4.0},  # A3
    {"pitch": 60, "start": start_time + 2.0, "end": start_time + 4.0},  # C4
    {"pitch": 64, "start": start_time + 2.0, "end": start_time + 4.0},  # E4
]

# Add the chord notes to the instrument
for note_info in em_chord + am_chord:
    note = pretty_midi.Note(
        velocity=65,  # Medium-soft for chords
        pitch=note_info["pitch"],
        start=note_info["start"],
        end=note_info["end"]
    )
    guitar.notes.append(note)

# Create a section mixing monophonic melody with bass notes (third measure)
start_time = 8.0
melody_with_bass = [
    # Bass notes
    {"pitch": 43, "start": start_time, "end": start_time + 1.0},  # G2 (bass)
    {"pitch": 47, "start": start_time + 1.0, "end": start_time + 2.0},  # B2 (bass)
    {"pitch": 50, "start": start_time + 2.0, "end": start_time + 3.0},  # D3 (bass)
    {"pitch": 43, "start": start_time + 3.0, "end": start_time + 4.0},  # G2 (bass)
    
    # Melody notes (slightly later to avoid playing exactly with bass)
    {"pitch": 62, "start": start_time + 0.25, "end": start_time + 0.75},  # D4
    {"pitch": 64, "start": start_time + 0.75, "end": start_time + 1.25},  # E4
    {"pitch": 67, "start": start_time + 1.25, "end": start_time + 1.75},  # G4
    {"pitch": 69, "start": start_time + 1.75, "end": start_time + 2.25},  # A4
    {"pitch": 71, "start": start_time + 2.25, "end": start_time + 2.75},  # B4
    {"pitch": 72, "start": start_time + 2.75, "end": start_time + 3.25},  # C5
    {"pitch": 74, "start": start_time + 3.25, "end": start_time + 3.75},  # D5
]

# Add the melody with bass notes to the instrument
for note_info in melody_with_bass:
    note = pretty_midi.Note(
        velocity=75 if note_info["pitch"] > 60 else 65,  # Louder melody, softer bass
        pitch=note_info["pitch"],
        start=note_info["start"],
        end=note_info["end"]
    )
    guitar.notes.append(note)

# Add a final chord (fourth measure)
start_time = 12.0
# G major chord with a bit of tremolo effect
g_major_final = [
    {"pitch": 43, "start": start_time, "end": start_time + 4.0},  # G2 (bass)
    {"pitch": 55, "start": start_time, "end": start_time + 4.0},  # G3
    {"pitch": 59, "start": start_time, "end": start_time + 4.0},  # B3
    {"pitch": 62, "start": start_time, "end": start_time + 4.0},  # D4
    {"pitch": 67, "start": start_time, "end": start_time + 4.0},  # G4
]

# Add the final chord notes to the instrument
for note_info in g_major_final:
    note = pretty_midi.Note(
        velocity=70,
        pitch=note_info["pitch"],
        start=note_info["start"],
        end=note_info["end"]
    )
    guitar.notes.append(note)

# Add some expression with pitch bends
# Classical guitar can have subtle pitch bends (vibrato)
pb = pretty_midi.PitchBend(pitch=200, time=13.0)  # Small bend, around 1/3 semitone
guitar.pitch_bends.append(pb)
pb = pretty_midi.PitchBend(pitch=0, time=13.5)  # Return to normal
guitar.pitch_bends.append(pb)
pb = pretty_midi.PitchBend(pitch=-200, time=14.0)  # Small bend down
guitar.pitch_bends.append(pb)
pb = pretty_midi.PitchBend(pitch=0, time=14.5)  # Return to normal
guitar.pitch_bends.append(pb)

# Add a control change for expression
cc = pretty_midi.ControlChange(number=11, value=100, time=12.5)  # Expression
guitar.control_changes.append(cc)
cc = pretty_midi.ControlChange(number=11, value=75, time=15.0)  # Decrease expression
guitar.control_changes.append(cc)

# Add the instrument to the PrettyMIDI object
classical_guitar.instruments.append(guitar)

# If you want to write this to a file, use:
classical_guitar.write('dataclassical_guitar_example.mid')

# Example of accessing information from the MIDI object
total_duration = classical_guitar.get_end_time()
print(f"Total duration: {total_duration} seconds")
print(f"Tempo: {classical_guitar.get_tempo_changes()[1][0]} BPM")
print(f"Total notes: {len(guitar.notes)}")
print(f"Note pitch range: {min([n.pitch for n in guitar.notes])} to {max([n.pitch for n in guitar.notes])}")

# To test if our polyphony constraint is respected, count max simultaneous notes:
def count_max_simultaneous_notes(notes):
    events = []
    for note in notes:
        events.append((note.start, 1))  # Note start
        events.append((note.end, -1))   # Note end
    
    events.sort()
    current_notes = 0
    max_notes = 0
    
    for _, change in events:
        current_notes += change
        max_notes = max(max_notes, current_notes)
    
    return max_notes

max_polyphony = count_max_simultaneous_notes(guitar.notes)
print(f"Maximum simultaneous notes: {max_polyphony}")

# This should confirm we never exceed 6 notes (the classical guitar constraint)
assert max_polyphony <= 6, "Exceeded classical guitar constraint of 6 notes maximum"
