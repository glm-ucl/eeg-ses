"""biosemi - Biosemi EEG support module."""

import os

class BdfFile():
    """bdf file reader class.

    Reads and decodes all bdf header fields and provides an interface for sequentially reading
    the channel data records."""

    byteorder = 'little'
    sampsize = 3

    def __init__(self, filename):
        self.filename = filename

    def __enter__(self):
        """Context manager entry - open the file in read mode, check for valid bdf identifier,
        extract header fields, and return instance."""
        self.file = open(self.filename, 'rb')
        assert self.file.read(8) == b'\xffBIOSEMI', self.filename + ' is not a valid bdf file.'
        self.subject_id = self.file.read(80).strip().decode()
        self.recording_id = self.file.read(80).strip().decode()
        self.startdate = self.file.read(8).decode()
        self.starttime = self.file.read(8).decode()
        self.headerlen = int(self.file.read(8).strip())
        self.version = self.file.read(44).strip().decode()
        self.nof_records = int(self.file.read(8).strip())
        self.duration = int(self.file.read(8).strip())
        self.nof_channels = int(self.file.read(4).strip())
        self.labels = self._str_field_list(16)
        self.transducers = self._str_field_list(80)
        self.dimensions = self._str_field_list(8)
        self.physmin = self._int_field_list(8)
        self.physmax = self._int_field_list(8)
        self.digimin = self._int_field_list(8)
        self.digimax = self._int_field_list(8)
        self.prefiltering = self._str_field_list(80)
        self.nof_samples = self._int_field_list(8)
        self.reserved = self._str_field_list(32)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close the file."""
        if self.file:
            self.file.close()

    def _str_field_list(self, size):
        """Read a channel array of string fields of size from the file."""
        fields = []
        for channel in range(self.nof_channels):
            fields.append(self.file.read(size).strip().decode())
        return fields

    def _int_field_list(self, size):
        """Read a channel array of integer fields of size from the file."""
        fields = []
        for channel in range(self.nof_channels):
            fields.append(int(self.file.read(size).strip()))
        return fields

    def seek(self, n):
        """Set the file stream position to the start of record n."""
        self.file.seek(BdfFile.sampsize * sum(self.nof_samples) * n + self.headerlen)

    @property
    def record(self):
        """Read and return the next complete data record,
        as a nof_channels length list of nof_samples length lists of signed integers."""
        record = []
        for channel in range(self.nof_channels):
            samples = []
            for sample in range(self.nof_samples[channel]):
                samples.append(int.from_bytes(
                    self.file.read(BdfFile.sampsize), BdfFile.byteorder, signed=True))
            record.append(samples)
        return record

    @property
    def trigstat(self):
        """Read and return the next trigger/status channel data record only,
        as a nof_samples length list of signed integers."""
        self.file.seek(BdfFile.sampsize * sum(self.nof_samples[:-1]), os.SEEK_CUR)
        samples = []
        for sample in range(self.nof_samples[self.nof_channels - 1]):
            samples.append(int.from_bytes(
                self.file.read(BdfFile.sampsize), BdfFile.byteorder, signed=True))
        return samples