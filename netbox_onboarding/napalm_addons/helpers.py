from enum import Enum


class GeneralDeploymentMode(Enum):
    def __str__(self):
        return '{0}'.format(self.name)

    @property
    def id(self):
        return self.value[0]

    @property
    def cls(self):
        return self.value[1]
