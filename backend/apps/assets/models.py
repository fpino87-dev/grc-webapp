from django.db import models

from core.models import BaseModel


class NetworkZone(BaseModel):
    plant = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    zone_type = models.CharField(
        max_length=10,
        choices=[("IT", "IT"), ("OT", "OT"), ("DMZ", "DMZ")],
    )
    purdue_level = models.IntegerField(null=True, blank=True)


class Asset(BaseModel):
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.CASCADE,
        related_name="assets",
    )
    name = models.CharField(max_length=200)
    asset_type = models.CharField(
        max_length=5,
        choices=[("IT", "IT"), ("OT", "OT")],
    )
    criticality = models.IntegerField(default=1)
    processes = models.ManyToManyField("bia.CriticalProcess", blank=True)
    owner = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-criticality", "name"]


class AssetIT(Asset):
    fqdn = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    os = models.CharField(max_length=100, blank=True)
    eol_date = models.DateField(null=True, blank=True)
    cve_score_max = models.FloatField(null=True, blank=True)
    internet_exposed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Asset IT"


class AssetOT(Asset):
    purdue_level = models.IntegerField()
    category = models.CharField(
        max_length=20,
        choices=[
            ("PLC", "PLC"),
            ("SCADA", "SCADA"),
            ("HMI", "HMI"),
            ("RTU", "RTU"),
            ("sensore", "Sensore"),
            ("altro", "Altro"),
        ],
    )
    patchable = models.BooleanField(default=False)
    patch_block_reason = models.TextField(blank=True)
    maintenance_window = models.CharField(max_length=100, blank=True)
    network_zone = models.ForeignKey(
        NetworkZone,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    vendor = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Asset OT"


class AssetDependency(BaseModel):
    from_asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="dependencies_from",
    )
    to_asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="dependencies_to",
    )
    dep_type = models.CharField(
        max_length=20,
        choices=[
            ("dipende_da", "Dipende da"),
            ("connesso_a", "Connesso a"),
        ],
    )

