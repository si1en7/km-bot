try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    import Image
import PIL.ImageOps
import pytesseract
import os
import sys
import re
import string
import database as DB
import cv2
import numpy as np
# define the image directory to process

global imgfileloc
imgfileloc = "screenshots/"
global aspect
'''
location of kill mail given a certain aspect ratio, scaled to a height of 1080 pixel
'''
aspect = {"1.33": (110, 185, 1330, 890), "1.43": (120, 164, 1428, 920), "1.6": (132, 120, 1598, 966), "1.77": (148, 72, 1776, 1012), "1.78": (148, 72, 1776, 1012), "1.79": (148, 72, 1776, 1012), "2": (
    322, 72, 1950, 1012), "ref": (322, 72, 1950, 1012), "3": (359, 72, 1981, 1010)}


global template
template = {1.3: "template/1.3.png",1.6:"template/1.6.png",1.7:"template/1.7.png", 2.1:"template/2.1.png"}
global cropCoords
'''
location of kill mail elements
'''
cropCoords = {
    "name": {
        "coord": (106, 76, 453, 109),
        "type": 1, 
        "resize": [.25,.19]
    },
    "isk": {
        "coord": (602, 125, 933, 162),
        "type": 2, 
        "resize": [0,0]
    },
    "time": {
        "coord": (18, 178, 216, 198),
        "type": 1, 
        "resize": [.4,.2]
    },
    "playership": {
        "coord": (595, 76, 928, 102),
        "type": 1, 
        "resize": [0,0]
    },
    "kmtype": {
        "coord": (85, 13, 360, 48),
        "type": 1, 
        "resize": [0,0]
    },
    # "playerid": {
    #     "coord": (79, 12, 352, 44),
    #     "type": 1
    # },
    "participants": {
        "coord": (15, 237, 168, 263),
        "type": 3, 
        "resize": [0,0]
    },
    "finalblow": {
        "coord": (77, 283, 303, 311),
        "type": 1, 
        "resize": [.15,.3]
    },
    "location": {
        "coord": (21, 197, 287, 220),
        "type": 1, 
        "resize": [.2,0]
    }
}


class Parser:
    def createlog(self,data,filename):
        file = open(f'logs/{filename}.txt',"w")
        for name,value in data.items():
            file.write(f'{name}:{value} \n')
    def checksize(self,filename):
        img = Image.open(f'screenshots/{filename}')
        print(f'{img.size[0]} x {img.size[1]}')
        if img.size[0] < 720 or img.size[1] < 960:
            return False
        
    def ssresize(self,filename):
        screenshot = Image.open(filename)
        width, height = screenshot.size
        ssratio = round(width/height,2)
        baseheight = 1080
        hpercent = (baseheight / float(screenshot.size[1]))
        wsize = int((float(screenshot.size[0]) * float(hpercent)))
        img = screenshot.resize((wsize, baseheight), Image.ANTIALIAS)
        img.save('output/resized_image.png')
        return (img.size[0],img.size[1])

    def sscrop(self,filename, coords):
        image_obj = Image.open(filename)
        cropped_image = image_obj.crop(coords)
        baseheight = 550
        hpercent = (baseheight / float(cropped_image.size[1]))
        wsize = int((float(cropped_image.size[0]) * float(hpercent)))
        cropped_image = cropped_image.resize((wsize, baseheight), Image.ANTIALIAS)
        cropped_image.save("output/cropped_current.png")

    def ssratio(self,filename):
        img = Image.open(filename)
        ratio = img.size[0]/img.size[1]
        if round(ratio,2) != 1.73:
            ratio = str(ratio)
            ratio = ratio[0:3]
            ratio = float(ratio)
            if ratio in template:
                return template[ratio]
            else:
                return False
    def resizeimage(self,name,percent):
        imagetemp = Image.open("output/"+name+".png")
        imagetemp = imagetemp.resize(
            (imagetemp.size[0]+int(imagetemp.size[0]*percent[0]), imagetemp.size[1]+int(imagetemp.size[1]*percent[1])), Image.ANTIALIAS)
        imagetemp.save("output/"+name+".png")

    def cropMail(self, coords, imageAdjust, output, file):
        image_obj = Image.open(file)
        cropped_image = image_obj.crop(coords)

        # invert cropped image
        if imageAdjust == 1:
            cropped_image = cropped_image.convert("L")
            cropped_image = PIL.ImageOps.invert(cropped_image)

        # sharpen and increase contrast
        if imageAdjust == 2:
            cropped_image = cropped_image.convert("L")
            cropped_image = PIL.ImageOps.invert(cropped_image)
            cropped_image = ImageEnhance.Contrast(cropped_image)
            cropped_image = cropped_image.enhance(5)

        # just sharpen
        if imageAdjust == 3:
            cropped_image = cropped_image.filter(ImageFilter.SHARPEN)
            filterimg = ImageEnhance.Contrast(cropped_image)
            cropped_image = filterimg.enhance(2)
        cropped_image.save(output)

    # shift given crop coordinates when all else fails (usually just on the x-axis)
    # def shiftCrop(self, coords, shift):
    #     newCoords = [0, 0, 0, 0]
    #     for count, value in enumerate(coords):
    #         value = int(value)
    #         if (count % 2) == 0:
    #             newCoords[count] = round(value + (value * shift))
    #         else:
    #             newCoords[count] = value
    #     return (newCoords[0], newCoords[1], newCoords[2], newCoords[3])

    # sanity checking OCR output, makes any corrections to input and returns it
    def verifyOutput(self, type, value):
        # minimum check for some type of corp tag followed by whatever due to wildly variable names and special characters
        # if type == "name" or:
        #     result = re.search(r'(\[[A-Z,0-9]*\])?.*', value)
        #     if result:
        #         return value
        #     else:
        #         return "error"
        # check for a minimum of 1,123 ISK and trim anything after ISK
        value = value.replace("\n","")
        value = value.replace("\"","")
        if type == "isk":
            translator = str.maketrans('', '', string.punctuation)
            isk = value.translate(translator)
            isk = str(re.findall("\d+", isk)[0])
            #result = re.search(r"([0-9]{1,3}[,])*[0-9]{3} [A-Z,a-z]{3}", value)
            print(isk)
            
            if isk.isnumeric():
                return isk
            else:
                return "error"
        # check for a date from 0000/00/00 00:00:00 UTC -0
        # 'UTC -0' optional because +/- value is unreliable
        if type == "time":
            date = value.split(" ")
            result = re.search(
                r"[0-9]{4}/[0-9]{2}/[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", f'{date[0]} {date[1]}')
            if result:
                return f'{date[0]} {date[1]}'
            else:
                return "error"
        # checking to see if ship detected partial matches one of the known ship types
        if type == "playership":
            playership = value.upper()
            shiptypes = ["Frigate", "Cruiser", "Battlecruiser",
                         "Industrial Ship", "Battleship", "Destroyer"]
            for shiptype in shiptypes:
                if playership.find(shiptype.upper()):
                    return value
                    break
                else:
                    return "error"
        # verify if KM is a kill or loss
        if type == "kmtype":
            result = re.search(r'(KILL)?(LOSS)? REPORT', value)
            if result:
                type = value.split(" ")
                return type[0]
            else:
                return "error"
        # if type == "playerid":
            # print(value)
            # result = re.search(r'.*(\[[I]?[i]?[D]?[0]?[O]?:[0-9]*\])', value)
            # if result:
            #     playerid = re.findall("\d+", value)[0]
            #     print(playerid)
            #     return playerid
            # else:
            #     result = re.search(r'(KILL)?(LOSS)? REPORT', value)
            #     if result:
            #         return "0"
            #     else:
            #         return "error"
            # playerid = value.split(":")
            # print(playerid.isnumeric())
            # sys.exit()
        # verify the number of participants
        if type == "participants":
            result = re.search(r"[A-Z][a-z]* \[[0-9]*\]", value)
            if result:
                count = re.findall("\d+", value)[0]
                return count
            else:
                return "error"
        # checking to see if OCR could detect a player with the final blow
        if type == "finalblow" or type == "name":
            
            if re.search(r'\[[A-Z,0-9]{2,4}[\)]', value):
                finder = value.find(")")
                value = value.replace(")", "]", 1)
            if re.search(r'\[[A-Z,0-9]{2,4}[J]', value):
                finder = value.find("J")
                value = value.replace("J", "]", 1)
            if "]" in value:
                result = re.search(r'\[[A-Z,0-9]{2,4}\][ ]?.*', value)
            if result:
                return value
            else:
                result = re.search(r'(\[[A-Z,0-9]*\])?.*', value)
            if result:
                return value
            else:
                return "error"
        # checking if location satisfies similar to 'whatever < whatever < whatever'
        if type == "location":
            result = re.search(r'[\s]{1}[<]{1}[\s]{1}', value)
            if result:
                return value
            else:
                return "error"

    # the killmail processor
    def processkm(self, filename, messageid,guildid):
        # cleanup, because crop will shift for > 2.11 ratio
        # remove files from previous run
        for oldname in os.listdir("output/"):
            os.remove("output/"+oldname)
        errors = 0
        # process given filename, must be .jpg or .png
        if filename.endswith(".png") or filename.endswith(".jpg") or filename.endswith(".jpeg"):
            if not self.checksize(filename):
                return 98
            templateimg = self.ssratio(f'screenshots/{filename}')

            if templateimg:
                self.ssresize(f"screenshots/{filename}")
                image= cv2.imread('output/resized_image.png')
                gray= cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

                template= cv2.imread(templateimg,0)
                result= cv2.matchTemplate(gray, template, cv2.TM_CCOEFF)
                min_val, max_val, min_loc, max_loc= cv2.minMaxLoc(result)

                height, width= template.shape[:2]

                top_left= max_loc
                bottom_right= (top_left[0] + width, top_left[1] + height)
                self.sscrop('output/resized_image.png',top_left+bottom_right)
            else:
                print("Does not match any known ratio. Skipping")
                return 8

            errortypes = []
            data = {}
            # for each crop area, create a single image to process
            for name, single in cropCoords.items():
                self.cropMail(single['coord'], single['type'],
                              "output/"+name+".png", "output/cropped_current.png")
                self.resizeimage(name,single["resize"])
                    
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

                try:
                    result = self.verifyOutput(name, pytesseract.image_to_string(
                        Image.open("output/"+name+".png"))[:-2])
                except:
                    result = "error"

                if result == "error":
                    errors = errors+1
                    errortypes.append(name)
                    if name == "time":
                        data[name] = "9999/09/09 00:00:00"
                    elif name == "isk":
                        
                        
                        data[name] = "123"
                       
                    else:
                        data[name] = "0"
                else:
                    data[name] = result
                print(f"{name}: {result}")
            data['message_id'] = messageid
            data['guild_id'] = guildid
            data['errors'] = errors
            data['filename'] = filename
            print(errortypes)
            print(data)
            if not os.path.exists("processed/"+filename):
                os.rename("screenshots/"+filename, "processed/"+filename)
            

            #database insert
            kmdb = DB.KMDB()
            if kmdb.checkduplicate(data,"killmail") == 0:
                if errors == 0:
                    kmdb.insertkm(data,"killmail")
                else:
                    if kmdb.checkduplicate(data,"killmail_fix") == 0:
                        kmdb.insertkm(data,"killmail_fix")
                    else:
                        errors = 99
            else:
                errors = 99
            #return error count so bot can react to message
            self.createlog(data,filename)
            return errors

#thing = Parser()
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# print(pytesseract.image_to_string(Image.open("output/kmtype.png"))[:-2])
#thing.processkm("818880863398920192_b166er.jpg", 812127631147401247, 812127631147401247)
