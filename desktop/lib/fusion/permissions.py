"""a jogosultság-ellenőrzés helye (M8: csak a kapu; a jogosultsági modell a backlogban — specifikáció 17. fejezet)

Minden API-hívás, amely eszközt, rendszerműveletet vagy más program adatát érinti, ezen megy át — így a későbbi
modellhez nem kell az API-t átírni. Képességek: "device:<szerep>", "system:<művelet>" (pl. system:bluetooth,
system:printers), "programs:manage".
"""


def check(program, capability):
    """most mindig engedélyez"""
    return True
