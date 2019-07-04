import logging

from ..native.memory import MemoryException
from ..core.smtlib import issymbolic

import microx

logger = logging.getLogger(__name__)

class MicroxEmulator(microx.Executor):
    """
    MicroxEmulator is a class used to execute arbitrary single
    instrucions with microx.
    """

    def __init__(self, cpu):
        super(MicroxEmulator, self).__init__(32)
        self._cpu = cpu


    def ReadRegisters(self):
        super(MicroxEmulator, self).ReadRegisters()


    def ReadReg(self, reg):
        value = self._cpu.read_register(reg)
        if issymbolic(value):
            raise abstractcpu.ConcretizeRegister(reg,
                "Concretizing {} register for microx".format(reg))
        super(MicroxEmulator, self).ReadReg(name, size, hint, value)


    def WriteReg(self, reg, value):
        super(MicroxEmulator, self).WriteReg(name, size, value)


    def ReadMem(self, seg, addr, num_bytes, write_perm):
        for i in xrange(num_bytes):
            location = addr + i
            value = self._cpu.load(location, 8)
            if issymbolic(value):
                raise abstractcpu.ConcretizeMemory(location, 8,
                    "Concretizing BYTE PTR {}:[{:08x}] for microx".format(seg, location))
            data.append(value)

    def WriteMem(self, seg, addr, data):
        pass

    def ReadFPU(self):
        return self.cpu.FPU

    def WriteFPU(self, fpu):
        self.cpu.FPU = fpu

    def Execute(self, num_execs):
        pass
