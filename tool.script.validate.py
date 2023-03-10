class ToolValidator:
  # Class to add custom behavior and properties to the tool and tool parameters.

    def __init__(self):
        # set self.params for use in other function
        self.params = arcpy.GetParameterInfo()      

    def initializeParameters(self):
        # Customize parameter properties. 
        # This gets called when the tool is opened.
        return

    def updateParameters(self):
        # Modify parameter values and properties.
        # This gets called each time a parameter is modified, before 
        # standard validation.
        try:
             if self.params[1].value:
                pass
             else:
                self.params[2].enabled = False
                self.params[3].enabled = False
                self.params[4].enabled = False
                self.params[5].enabled = False
                self.params[6].enabled = False
                self.params[7].enabled = False
                
             if 'Access Roads' in self.params[1].values:
                self.params[2].enabled = True
                self.params[5].enabled = True
             else:
                self.params[2].enabled = False
                self.params[5].enabled = False
                
             if 'Crane Path' in self.params[1].values:
                self.params[3].enabled = True
                self.params[6].enabled = True
             else:
                self.params[3].enabled = False
                self.params[6].enabled = False
                
             if 'Shared Path' in self.params[1].values:
                self.params[4].enabled = True
                self.params[7].enabled = True
             else:
                self.params[4].enabled = False
                self.params[7].enabled = False

        except TypeError:
            pass
 
            
        return

    def updateMessages(self):
        # Customize messages for the parameters.
        # This gets called after standard validation

        return

    # def isLicensed(self):
    #     # set tool isLicensed.
    # return True

    # def postExecute(self):
    #     # This method takes place after outputs are processed and
    #     # added to the display.
    # return