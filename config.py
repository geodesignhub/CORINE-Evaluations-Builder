settings = {

    "aoibounds": (11.4869,48.1519,11.6222,48.2423),
    "systems": ["URB",],
    "outputdirectory": "output",
    "workingdirectory": "working",
    "corinedata": "MUNICH-CORINE.zip",
}


processchains = {
    "URB": {
        "red": [111],
        "yellow": [],
        "green": [112,121,123,124, 131, 132,133,142, 211, 212,213,221,222,223, 231,241, 242, 243, 244, 311,312,313,321,323,324,333]
    },
    "AG": {
        "red": [211, 212,213,221,222,223,241,241,243,244],
        "yellow": [],
        "green": [321,322,323,324,333,334,411,412,141]
    },
    
    "IND": {
        "red": [121,122,123,124,131,132,133,123,124,131,132,133],
        "yellow": [],
        "green": [112,211, 212,213,221,222,223, 231,241, 242, 243, 244, 311,312,313,321,323,324,333,334]
    },
    
    "FOR": {
        "red": [311,312,313],
        "yellow": [],
        "green": [321,322,323,324,333,334,211,212,213,221,222,223,241,242,243,244,412]
    },
    
    "HYDRO": {
        "red": [511,512,521,522],
        "yellow": [],
        "green": [511,512,521,522]
    },
    

}
