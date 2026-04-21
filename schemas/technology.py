from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class EngineeringParameter(BaseModel):
    """
    A normalized engineering parameter extracted from a source.

    Examples:
    - capacity = 2 MW
    - water_depth = 33 m
    - rotor_diameter = 260 m
    - wave_height = 18 m
    - hydrogen_output = 400 kg/day
    """
    field_name: str = Field(..., description="Normalized parameter name")
    value: str = Field(..., description="Parameter value as stated or normalized")
    unit: Optional[str] = Field(default=None, description="Unit if available")
    note: Optional[str] = Field(default=None, description="Context or qualifier for the parameter")


class SourceReference(BaseModel):
    """
    A source reference attached to a profile or specific finding.
    """
    title: Optional[str] = Field(default=None, description="Source title")
    organization: Optional[str] = Field(default=None, description="Source organization or publisher")
    url: Optional[str] = Field(default=None, description="Source URL")
    publication_date: Optional[str] = Field(default=None, description="Publication date if available")
    access_date: Optional[str] = Field(default=None, description="Collection or access date")
    source_type: Optional[str] = Field(
        default=None,
        description="official, media, technical_report, paper, certification_body, etc."
    )


class TimelineMilestone(BaseModel):
    """
    A dated milestone in the lifecycle of a technology, project, or company.
    """
    date: Optional[str] = Field(default=None, description="Date or time period")
    event: str = Field(..., description="Milestone description")
    status: Optional[str] = Field(
        default=None,
        description="announced, tested, installed, commissioned, certified, funded, commercialized, etc."
    )


class TechnologyProfile(BaseModel):
    """
    Core structured technology / project profile for the intelligence collector.

    This model is intentionally broad enough to represent:
    - a technology route
    - a device or product
    - a demonstration project
    - a commercial project
    - a platform concept
    """

    # Basic identity
    name: str = Field(..., description="Name of the technology, device, platform, or project")
    aliases: List[str] = Field(default_factory=list, description="Alternative names or abbreviations")

    # Entity / organization
    company: Optional[str] = Field(default=None, description="Lead company if applicable")
    institution: Optional[str] = Field(default=None, description="Research institution / university / lab")
    consortium: Optional[str] = Field(default=None, description="Consortium or multi-party developer")
    country: Optional[str] = Field(default=None, description="Primary country")
    region: Optional[str] = Field(default=None, description="Region or site geography")

    # Topic classification
    energy_type: Optional[str] = Field(
        default=None,
        description="offshore wind, floating wind, wave energy, tidal energy, current energy, floating solar, offshore hydrogen, integrated ocean energy, etc."
    )
    tech_route: Optional[str] = Field(
        default=None,
        description="Normalized technology route, e.g. oscillating body, OWC, overtopping, direct seawater electrolysis, semi-submersible, TLP, etc."
    )
    system_type: Optional[str] = Field(
        default=None,
        description="device, platform, project, pilot, infrastructure, port, vessel, energy island, etc."
    )
    application_scenario: Optional[str] = Field(
        default=None,
        description="Grid supply, island power, offshore oil and gas, desalination, hydrogen production, hybrid platform, etc."
    )

    # Deployment / configuration
    deployment: Optional[str] = Field(
        default=None,
        description="fixed, floating, nearshore, offshore, onshore-coupled, centralized offshore, distributed offshore, etc."
    )
    structural_form: Optional[str] = Field(
        default=None,
        description="semi-submersible, spar, TLP, barge, point absorber, submerged buoy, breakwater-mounted, etc."
    )
    mooring_or_foundation: Optional[str] = Field(
        default=None,
        description="single-point mooring, catenary mooring, tension-leg, gravity base, pile, etc."
    )
    material_system: Optional[str] = Field(
        default=None,
        description="steel, concrete, hybrid steel-concrete, composite, UHPC, etc."
    )
    installation_method: Optional[str] = Field(
        default=None,
        description="tow-out, quayside assembly, offshore heavy lift, modular assembly, etc."
    )
    o_and_m_features: Optional[str] = Field(
        default=None,
        description="Maintenance and operations characteristics"
    )

    # Performance and engineering parameters
    capacity: Optional[str] = Field(default=None, description="Nominal capacity, e.g. 2 MW, 100 kW")
    hydrogen_output: Optional[str] = Field(default=None, description="Hydrogen output if applicable")
    water_depth: Optional[str] = Field(default=None, description="Water depth or deployment depth")
    scale_description: Optional[str] = Field(
        default=None,
        description="Scale of project or array, e.g. single device, 3-device array, 400 MW project"
    )
    engineering_parameters: List[EngineeringParameter] = Field(
        default_factory=list,
        description="Normalized engineering parameters extracted from sources"
    )

    # Technical description
    principle_of_operation: Optional[str] = Field(
        default=None,
        description="Short explanation of how the system works"
    )
    key_components: List[str] = Field(default_factory=list, description="Main technical components")
    engineering_features: List[str] = Field(
        default_factory=list,
        description="Notable engineering characteristics"
    )

    # Value proposition and limitations
    advantages: List[str] = Field(default_factory=list, description="Claimed or inferred advantages")
    limitations: List[str] = Field(default_factory=list, description="Known limitations or uncertainties")
    environmental_considerations: List[str] = Field(
        default_factory=list,
        description="Environmental impact or environmental value points"
    )

    # Maturity and commercialization
    maturity: Optional[str] = Field(
        default=None,
        description="concept, lab validation, tank test, sea trial, pilot, demonstration, pre-commercial, commercial"
    )
    commercialization_status: Optional[str] = Field(
        default=None,
        description="Narrative status of commercialization"
    )
    certification_status: Optional[str] = Field(
        default=None,
        description="AiP, DNV feasibility statement, grid connected, certified, etc."
    )
    trl: Optional[str] = Field(default=None, description="Technology readiness level if available")

    # Strategic / intelligence interpretation
    significance: Optional[str] = Field(
        default=None,
        description="Why this case matters from an engineering or industrial standpoint"
    )
    comparison_tags: List[str] = Field(
        default_factory=list,
        description="Tags used later for comparison, e.g. modularity, survivability, low-maintenance"
    )
    watchpoints: List[str] = Field(
        default_factory=list,
        description="What should be tracked next"
    )

    # Timeline
    timeline: List[TimelineMilestone] = Field(
        default_factory=list,
        description="Key milestones"
    )

    # Evidence and provenance
    sources: List[SourceReference] = Field(
        default_factory=list,
        description="Supporting sources"
    )
    source_reference: Optional[str] = Field(
        default=None,
        description="Short source reference string for quick use in reports"
    )

    # Internal notes
    collector_note: Optional[str] = Field(
        default=None,
        description="Internal note written by the collector"
    )
    uncertainty_note: Optional[str] = Field(
        default=None,
        description="Explicit note about uncertainty or incomplete evidence"
    )


class ComparisonDimension(BaseModel):
    """
    Represents one comparison dimension across multiple technology profiles.
    """
    dimension: str = Field(..., description="Comparison dimension name")
    observation: str = Field(..., description="Cross-case observation")
    stronger_cases: List[str] = Field(default_factory=list, description="Cases that appear stronger on this dimension")
    weaker_cases: List[str] = Field(default_factory=list, description="Cases that appear weaker or less proven")
    note: Optional[str] = Field(default=None, description="Caution or nuance")


class ComparisonResult(BaseModel):
    """
    Result of comparing multiple technology profiles.
    """
    topic: str = Field(..., description="Comparison topic")
    included_cases: List[str] = Field(default_factory=list, description="Case names included in the comparison")
    dimensions: List[ComparisonDimension] = Field(default_factory=list, description="Comparison by dimension")
    key_differences: List[str] = Field(default_factory=list, description="Major cross-case differences")
    notable_patterns: List[str] = Field(default_factory=list, description="Industry or technology patterns observed")
    commercialization_observation: Optional[str] = Field(default=None, description="Commercialization-level takeaway")
    engineering_observation: Optional[str] = Field(default=None, description="Engineering-level takeaway")
    open_questions: List[str] = Field(default_factory=list, description="Remaining uncertainties or questions")


class TrendAnalysis(BaseModel):
    """
    Trend-level synthesis across cases and evidence.
    """
    topic: str = Field(..., description="Topic analyzed")
    observed_trends: List[str] = Field(default_factory=list, description="Evidence-backed trends")
    bottlenecks: List[str] = Field(default_factory=list, description="Technical or industrial bottlenecks")
    opportunity_areas: List[str] = Field(default_factory=list, description="Potential opportunity areas")
    watchpoints: List[str] = Field(default_factory=list, description="Items worth monitoring")
    editorial_note: Optional[str] = Field(default=None, description="Concise editorial-style note")


class IntelligenceGap(BaseModel):
    """
    An identified gap in the current intelligence collection.
    """
    gap: str = Field(..., description="What is missing or unclear")
    why_it_matters: str = Field(..., description="Why the gap matters for judgment or reporting")
    priority: str = Field(..., description="high, medium, low")


class IntelligenceReportPackage(BaseModel):
    """
    A complete package used for generating final report outputs.
    """
    topic: str = Field(..., description="Main research topic")
    background: Optional[str] = Field(default=None, description="Topic background summary")
    cases: List[TechnologyProfile] = Field(default_factory=list, description="Structured case profiles")
    comparison: Optional[ComparisonResult] = Field(default=None, description="Cross-case comparison")
    trend_analysis: Optional[TrendAnalysis] = Field(default=None, description="Trend synthesis")
    gaps: List[IntelligenceGap] = Field(default_factory=list, description="Known gaps")
    sources: List[SourceReference] = Field(default_factory=list, description="All main sources used")