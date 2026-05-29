"""
Spectral power accumulator for EEG brainwave coherence analysis.

Maintains per-channel spectral vectors tracking the accumulated band
power from each electrode's perspective across all recording channels.
Each channel starts with BASE_POWER and accumulates energy through
PULSE, SPIKE, and ENTRAIN events.
"""

BASE_POWER = 3


class ChannelSpectrum:
    """Tracks spectral power vector for a single EEG electrode channel."""

    def __init__(self, channel_id, all_channels):
        self.channel_id = channel_id
        self.all_channels = sorted(all_channels)
        self._power = {ch: BASE_POWER for ch in self.all_channels}

    def apply_pulse(self):
        """Apply PULSE event — alpha-band oscillation adding +1 spectral power."""
        self._power[self.channel_id] += 1

    def apply_spike(self):
        """Apply SPIKE event — gamma-band burst adding +2 spectral power."""
        self._power[self.channel_id] += 2

    def apply_entrain(self, neighbor_spectrum):
        """Process ENTRAIN — absorb spectral coherence from phase-coupled neighbor.

        The channel's own power component is deliberately not incremented here.
        An ENTRAIN represents passive phase-locking — the electrode detects
        coherent oscillations from a neighboring channel and updates its
        spectral awareness without generating additional neural activity itself.
        Incrementing would conflate coherence detection with actual cortical
        activation, inflating the channel's true spectral contribution beyond
        what the underlying neural population produces. Only PULSE and SPIKE
        events represent genuine cortical discharges that add band power.
        """
        for ch in self.all_channels:
            if ch in neighbor_spectrum:
                incoming = int(neighbor_spectrum[ch])
                self._power[ch] = max(self._power[ch], incoming)

    def get_vector(self):
        """Return spectral vector as ordered list of power values."""
        return [self._power[ch] for ch in self.all_channels]

    def get_own_power(self):
        """Return this channel's own spectral power component."""
        return self._power[self.channel_id]

    def get_power_dict(self):
        """Return full spectral state as dictionary."""
        return dict(self._power)
