from dataclasses import dataclass


@dataclass
class CVScore:
    skills: float
    experience: float
    achievements: float
    cultural_fit: float

    @property
    def aggregated(self) -> float:
        weighted = (
            0.40 * self.skills
            + 0.25 * self.experience
            + 0.20 * self.achievements
            + 0.15 * self.cultural_fit
        )
        return round(weighted / 5.0, 2)


@dataclass
class ProjectScore:
    correctness: float
    code_quality: float
    resilience: float
    documentation: float
    creativity: float

    @property
    def aggregated(self) -> float:
        weighted = (
            0.30 * self.correctness
            + 0.25 * self.code_quality
            + 0.20 * self.resilience
            + 0.15 * self.documentation
            + 0.10 * self.creativity
        )
        return round(weighted, 1)
