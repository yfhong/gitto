from twisted.application.service import ServiceMaker

Gitto = ServiceMaker(
    "Gitto",
    "gitto.tap",
    "Poor man's git hosting",
    "gitto")
