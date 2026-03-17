GATEWAY:hopen 5050

// API arguments dictionary.
args: (!) . flip (
    (`table;       `taxi);
    (`column;     `fare);
    (`multiplier;  10j)
    );

// Extra options dictionary.
/opts: enlist[`timeout]!enlist timeout;
opts:()!()

// Response callback for asynchronous queries.
callback: {[hdr; pl] show (hdr; pl); };

/GATEWAY (`.example.daAPI; args; `callback; opts)
r:GATEWAY (`.example.daAPI; args; `; opts);

1 "Meta data:\n";
show r[0]
1 "\nPayload:\n";
show r[1]

exit 0
