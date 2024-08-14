import os
import shutil
import cv2
import math
import numpy as np
import pandas as pd
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor
import torch
from torchvision import transforms
from PIL import Image
from operator import itemgetter
from PIL import Image
import io
import traceback
import logging
import time
import warnings
from decouple import config

#device = torch.device("cpu")
#from LaptopCom.settings import MODEL_PATH, CONFIG_PATH

warnings.filterwarnings("ignore", category=UserWarning)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),  # Log to the terminal
        logging.FileHandler("inference_run_log.txt", mode="a"),  # Log to a file
    ]
)

# set other loggers to warning
logging.getLogger('detectron2').setLevel(logging.WARNING)
logging.getLogger("fvcore.common.checkpoint").setLevel(logging.WARNING)

def get_model(model_path, config_path, threshold):
    # Create config
    cfg = get_cfg()
    cfg.merge_from_file(config_path)
    if torch.cuda.is_available():
        cfg.MODEL.DEVICE = 'cuda'
    else:
        cfg.MODEL.DEVICE = 'cpu'
        # logging.info("CUDA is not available. Using CPU.")
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = threshold
    cfg.MODEL.WEIGHTS = model_path
    

    return DefaultPredictor(cfg), cfg



def fan_blade_count(img):
    midpoint=(int(img.shape[1]/2),int(img.shape[0]/2))
    radius=img.shape[1]/2
    # Convert to graycsale
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Blur the image for better edge detection
    img_blur = cv2.GaussianBlur(img_gray, (5,5), 0)
    
    # Canny Edge Detection
    edges = cv2.Canny(image=img_blur, threshold1=30, threshold2=100) # Canny Edge Detection
    output = img.copy()
    
    blade_number_list=[]
    radius_percentage=[12,14,16,18]
    cv2.imwrite("edge.jpg",edges)
    
    for percent in radius_percentage:
    
        #draw a green circle across the fan blade
        cv2.circle(output, midpoint, int(radius-(radius*percent/100)), (0, 255, 0), 1)
        cv2.imwrite("out.jpg",output)
    
        b,g,r=cv2.split(output)
        mask_circle = (b ==0) & (g == 255) & (r == 0)
    
        true_pixels= np.where(mask_circle==True)
        #arrange the circle coordinates
        circle_coordinates =[]
        for i in range(len(true_pixels[0])):
            
            (dx, dy) = (true_pixels[1][i]-midpoint[0], true_pixels[0][i]-midpoint[1])
            angle = math.degrees(math.atan2(float(dy), float(dx)))% 360
                  
            circle_coordinates.append([true_pixels[1][i],true_pixels[0][i],angle])
            
        circle_coordinates.sort(key = lambda circle_coordinates: circle_coordinates[2])
              
        blade_number=0
        white_encounter=None    
        dist_list=[]
        blade_dist=0
        for item in circle_coordinates:
            
            
            if white_encounter==None:
                
                if edges[item[1],item[0]]==255:
                    white_encounter=1
                    blade_number+=1
                    
                    dist_list.append(blade_dist)    
                    blade_dist=0                
                    
                    cv2.circle(output, (item[0], item[1]), 1, (0, 0, 255), -1)
                else:
                    white_encounter=0
                    
            elif white_encounter==1:
                
                if edges[item[1],item[0]]==0:
                    white_encounter=0
                                    
                    
            elif white_encounter==0:
                cv2.circle(output, (item[0], item[1]), 1, (0, 0, 255), -1)
                
    
                if edges[item[1],item[0]]==255:
                    white_encounter=1
                    blade_number+=1
                    
                    dist_list.append(blade_dist)
                    blade_dist=0                
                    
            blade_dist+=1
                                                           
        #blade_number=int(blade_number/2)
        
        #average_len=sum(dist_list)/len(dist_list)
        mode_len=(max(set(dist_list), key=dist_list.count))
        mean_len=sum(dist_list)/len(dist_list)
        
        
        
        #logging.info(dist_list)
        highest_len=max(dist_list)
        #logging.info(dist_list)
        lowest_len=min(dist_list)
        
        
        #check if portion of smallest dist over certain percentage
        current_valid=[item for item in set(dist_list) if (dist_list.count(item))/len(dist_list)>0.25 and item >0 ]
        
        try:
            current_valid= min(current_valid)
        except:
            current_valid= 0
        
        
        
        #current dist
        current_dist=0
        determine_dist=0
        count_dist=0

        count_current_valid=0
        
        
        
        #logging.info(abs(mode_len-highest_len)/mode_len)
        
        if current_valid==0:
            if abs(mode_len-highest_len)/mode_len <10:
                blade_number=int(len(circle_coordinates)/(sum(dist_list)/len(dist_list)))
            else:
                blade_number=int(len(circle_coordinates)/mode_len)
                
        else:
            blade_number=int(len(circle_coordinates)/current_valid)
            #logging.info("oii")
            count_current_valid+=1
            
        blade_number=int(blade_number/2)
        #logging.info(blade_number)
        blade_number_list.append(blade_number)
    
    if count_current_valid>=1:
        blade_number=int(sum(blade_number_list)/len(blade_number_list))
    else:
        blade_number=max(blade_number_list)
    
    return blade_number


def get_image_data(predictor: object, input_image_path: str, raw_image, model, device) -> dict:
    fan_num = 0
    heat_pipe_num = 0

    image = cv2.imread(input_image_path)  # input
    dimension_image = image.copy()

    outputs = predictor(image)  # inference

    mask_array = outputs['instances'].pred_masks.to("cpu").numpy()
    num_instances = mask_array.shape[0]
    scores = outputs['instances'].scores.to("cpu").numpy()
    labels = outputs['instances'].pred_classes.to("cpu").numpy()
    must_exist = [16, 17, 1]
    if num_instances!=0 and any(label in labels for label in must_exist):
        
        bbox = outputs['instances'].pred_boxes.to("cpu").tensor.numpy()

        diameter = []
        fan_width_pixel = []
        blade_number=[]
        pipe_width_pixel = None
        battery_width_pixel = None

        circuitboard_points=[image.shape[1],image.shape[0],0,0]    #min_width,min_height,max_width,max_height

        #get the list of classes from txt
        with open('classes.txt', 'r') as f:
            classes = f.read().splitlines() 
        
        #prepare a dictionary for ports counting
        ports=[]    
        angled_blade=False

        #v = Visualizer(image[:, :, ::-1], MetadataCatalog.get(cfg.DATASETS.TRAIN[0]), scale=1.2) #masking
        #v = v.draw_instance_predictions(outputs["instances"].to("cpu"))
        
        #cv2.imwrite(input_image_path.split(".jpg")[0]+'_segmentation.jpg', v.get_image()[:, :, ::-1])            

        for i in range(num_instances):
            if labels[i] == 17:  # count fan number
                fan_num += 1
            elif labels[i] == 1:  # count heat pipe and get the width
                
                try:
                    mid_point1 = int(bbox[i][0] + ((bbox[i][2] - bbox[i][0]) / 2))
                    mid_point2 = int(bbox[i][1] + ((bbox[i][3] - bbox[i][1]) / 2))
        
                    width_axis1 = mask_array[i][:, mid_point1:mid_point1 + 1].copy()
                    width_axis2 = mask_array[i][mid_point2:mid_point2 + 1, :].copy()
        
                    width_axis_result1 = np.where(width_axis1 == True)[0]
                    width_axis_result2 = np.where(width_axis2 == True)[1]
        
                    min_width_axis1 = width_axis_result1[0]
                    max_width_axis1 = width_axis_result1[-1]
        
                    min_width_axis2 = width_axis_result2[0]
                    max_width_axis2 = width_axis_result2[-1]
        
                    if (max_width_axis1 - min_width_axis1) < (max_width_axis2 - min_width_axis2):
                        pipe_width_pixel = max_width_axis1 - min_width_axis1
                    else:
                        pipe_width_pixel = max_width_axis2 - min_width_axis2
                        
                    heat_pipe_num += 1
                except:
                    continue
                
            elif labels[i] == 16:  # fanblade
                # diameter
                diameter.append(bbox[i][3] - bbox[i][1])
                # logging.info(abs(((bbox[i][3] - bbox[i][1])-(bbox[i][2] - bbox[i][0])))/(bbox[i][3] - bbox[i][1]))
                if abs(((bbox[i][3] - bbox[i][1])-(bbox[i][2] - bbox[i][0])))/(bbox[i][3] - bbox[i][1]) > 0.095:
                    angled_blade=True

                mid_point_x = int(bbox[i][0] + ((bbox[i][2] - bbox[i][0]) / 2))
                mid_point_y = int(bbox[i][1] + ((bbox[i][3] - bbox[i][1]) / 2))
                # centre_point = (mid_point_x, mid_point_y)

                # blade count
                try:
                    blade_number.append(fan_blade_count(dimension_image[int(bbox[i][1]):int(bbox[i][3]),
                                                int(bbox[i][0]):int(bbox[i][2])]))
                except:
                    blade_number.append(0)

                # fan dimension
                try:
                    whole_fan_index = [i for i in range(len(bbox)) if (bbox[i][0] < mid_point_x) and
                                    (bbox[i][2] > mid_point_x) and (bbox[i][1] < mid_point_y) and
                                    (bbox[i][3] > mid_point_y) and labels[i] == 17][0]
        
                    mid_point_fan = mid_point_x
                    width_axis_fan = mask_array[whole_fan_index][:, mid_point_fan:mid_point_fan + 1].copy()
        
                    width_axis_result_fan = np.where(width_axis_fan == True)[0]
                    #logging.info(width_axis_fan)
                    min_width_axis_fan = width_axis_result_fan[0]
                    max_width_axis_fan = width_axis_result_fan[-1]
        
                    fan_width_pixel.append(max_width_axis_fan - min_width_axis_fan)
                except:
                    fan_width_pixel.append(0)
                    
                '''
            elif labels[i] == 4:  # circuitboard


                min_y = min(np.where(mask_array[i]==True)[0])
                max_y = max(np.where(mask_array[i]==True)[0])
                
                min_x = min(np.where(mask_array[i]==True)[1])
                max_x = max(np.where(mask_array[i]==True)[1])            
                
                if circuitboard_points[0] > min_x:
                    circuitboard_points[0]=min_x
                
                if circuitboard_points[1] > min_y:
                    circuitboard_points[1]=min_y

                if circuitboard_points[2] < max_x:
                    circuitboard_points[2]=max_x

                if circuitboard_points[3] < max_y:
                    circuitboard_points[3]=max_y
                    
                if circuitboard_points[3]-circuitboard_points[1] <circuitboard_points[2]-circuitboard_points[0]:
                    board_width_pixel=circuitboard_points[3]-circuitboard_points[1]
                        
                else:
                    board_width_pixel=circuitboard_points[2]-circuitboard_points[0]

            elif labels[i] == 5:  # battery

                mid_point1= int(bbox[i][0] + ((bbox[i][2]-bbox[i][0])/2))
                mid_point2= int(bbox[i][1] + ((bbox[i][3]-bbox[i][1])/2)) 

                width_axis1 = mask_array[i][:, mid_point1:mid_point1 + 1].copy()
                width_axis2 = mask_array[i][mid_point2:mid_point2 + 1, :].copy()

                width_axis_result1 = np.where(width_axis1==True)[0]
                width_axis_result2 = np.where(width_axis2==True)[1]

                min_width_axis1 = width_axis_result1[0]
                max_width_axis1 = width_axis_result1[-1]

                min_width_axis2 = width_axis_result2[0]
                max_width_axis2 = width_axis_result2[-1]

                if (max_width_axis1 - min_width_axis1) < (max_width_axis2 - min_width_axis2):
                    battery_width_pixel = max_width_axis1 - min_width_axis1
                else:
                    battery_width_pixel = max_width_axis2 - min_width_axis2
                    
            '''       
            elif not labels[i]==19:   #count ports
                ports.append({"name":classes[labels[i]], "midx":int(bbox[i][0] + ((bbox[i][2] - bbox[i][0]) / 2))})
            
            
            '''
            if len(blade_number)>1:
                max_dimension= max(fan_width_pixel)
                remove_index=[]
                
                for k in range(len(fan_width_pixel)):
                    if max_dimension==0 or abs(max_dimension-fan_width_pixel[k])/max_dimension>0.8:
                        remove_index.append(k)
                        
                for item_index in remove_index:
                    blade_number.pop(item_index)
                    fan_width_pixel.pop(item_index)
                    fan_num-=1
            '''
                    

        ####side classification####
        class_names=['front','left','rear','right']
        # Preprocessing transformations
        preprocess=transforms.Compose([
                transforms.Resize(size=256),
                transforms.CenterCrop(size=224),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406],
                                    [0.229, 0.224, 0.225])
            ])   
        # img=Image.open(input_image_path).convert('RGB')
        img = raw_image
        inputs=preprocess(img).unsqueeze(0).to(device)
        outputs_side = model(inputs)
        _, preds = torch.max(outputs_side, 1) 
        # logging.info(preds)    
        side_label=class_names[preds]

            
        ####side classification####    
        
        #order detected ports
        if side_label=="right":
            ports=sorted(ports, key=itemgetter('midx'), reverse=True)
        else:
            ports=sorted(ports, key=itemgetter('midx'), reverse=False)
            
        ordered_port=[]
        
        for port in ports:
            ordered_port.append(port["name"])    

        full_data = {"Fan Number": fan_num, "Fan Blade Number": blade_number,
                    "Fan Diameter": diameter, "Fan Dimension": fan_width_pixel,
                    "Heat Pipe Number": heat_pipe_num, "Heat Pipe Width": pipe_width_pixel,
                    "Battery Width":battery_width_pixel,"Side":side_label,"Ports":ordered_port,
                    "angled_Blade":angled_blade}
        #merge with port dictionary
        #full_data.update(ports)
        
        return full_data, num_instances, labels, scores

    else:
        return None
    
def process_single_image(predictor, model, device, file_path, review_hash_id, row_num, total_row_count):
    try:
        raw_image =  Image.open(file_path).convert('RGB')
        get_img_data = get_image_data(predictor, f"{file_path}", raw_image, model, device)
        # os.remove(f"{file_name}")
        if not get_img_data==None:
            extracted_data, num_instances, labels, scores = get_img_data
            if extracted_data!=None:
                all_data = {
                    'image_file_name': file_name,
                    'num_instances':num_instances,
                    'labels': labels.tolist(),
                    'scores': scores.tolist(),
                    'extracted_data': extracted_data,
                }
                logging.info(f"Found data in {file_name} for hash_id: {review_hash_id}, row_num = {row_num+1}/{total_row_count}")
                return all_data
        return None
    except Exception as e:
        pass
        # logging.error(f"Error occured while processing {file_name} for hash_id: {review_hash_id}, row_num = {row_num+1}/{total_row_count}. Proceeding to next image.")

def update_row_in_csv(data, csv_file_path):
    try:
        df = pd.read_csv(csv_file_path, encoding="utf-8-sig")
        for row in data:
            df.loc[df['HASH_ID'] == row[-1], [
                "NUMBER_OF_HEATPIPES", "HEATPIPE_WIDTH", "NUMBER_OF_FANS", "FAN_DIMENSION", 
                "BLADE_COUNT", "LLM_PORTS_LEFT", "LLM_PORTS_RIGHT", "LLM_PORTS_REAR", 
                "LLM_PORTS_FRONT", "VC", "SELECTED_THERMAL_IMAGE_FILE"
            ]] = row[:-1]
        df.sort_values(by='PUBLISHED_DATE', ascending=False).to_csv(csv_file_path, index=False, encoding="utf-8-sig")
        logging.info("CSV updated successfully")
    except Exception as e:
        logging.error(f"Error updating CSV: {e}")

if __name__ == '__main__':
    start_time = time.time()
    logging.info("Script started")

    CWD = config("CWD")
    OUTPUT_CSV_FOLDER = config("OUTPUT_CSV_FOLDER")
    OUTPUT_CSV_NAME = config("OUTPUT_CSV_NAME")
    CSV_FILE_PATH = f"{OUTPUT_CSV_FOLDER}/{OUTPUT_CSV_NAME}"

    # Get the current working directory
    current_dir = os.getcwd()

    # Extract the actual directory name from the current path
    current_dir_name = os.path.basename(current_dir)

    # Check if the current directory name matches the expected name
    if current_dir_name != CWD:
        print(f"Incorrect working directory. Please cd into {CWD}")
    else:
        try:
            # Load the unprocessed data
            df = pd.read_csv(CSV_FILE_PATH, encoding="utf-8-sig")
            review_rows = df[(df['SELECTED_THERMAL_IMAGE_FILE'].isnull() | (df['SELECTED_THERMAL_IMAGE_FILE'] == '')) & (pd.to_datetime(df['PUBLISHED_DATE']) > pd.Timestamp('2023-05-27'))].sort_values(by='PUBLISHED_DATE', ascending=False)
            total_row_count = len(review_rows)

            if not review_rows.empty:
                # Load model
                threshold = 0.9
                predictor, cfg = get_model("model_final.pth", "config.yml", threshold)  # define the predictor

                # Side classification model
                MODEL = 'model.pth'
                model = torch.load(MODEL, map_location=torch.device('cpu'))
                model.eval()
                device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

                for row_num, review_row in review_rows.iterrows():
                    review_hash_id = review_row['HASH_ID']
                    selected_thermal_image_file = review_row['SELECTED_THERMAL_IMAGE_FILE']

                    if pd.notnull(selected_thermal_image_file):
                        logging.info(f"Already inferred hash_id: {review_hash_id}, row_num = {row_num + 1}/{total_row_count}")
                    else:
                        logging.info(f"Processing hash_id: {review_hash_id}, row_num = {row_num + 1}/{total_row_count}")

                        # Find matching dir to HASH_ID
                        image_directory = os.path.join("images", review_hash_id)
                        if not os.path.exists(image_directory):
                            logging.info(f"Image directory not found for hash_id: {review_hash_id}, row_num = {row_num + 1}/{total_row_count}")

                        image_files = os.listdir(image_directory)

                        all_data = []
                        for file_name in image_files:
                            result = process_single_image(predictor, model, device, os.path.join(image_directory, file_name), review_hash_id, row_num, total_row_count)
                            if result:
                                all_data.append(result)


                        extracted_data = None
                        best_image_file_name = None
                        if not all_data:
                            best_image_file_name = "not_found"
                        elif len(all_data) == 1:
                            extracted_data = all_data[0]['extracted_data']
                            best_image_file_name = all_data[0]['image_file_name']
                        else:
                            filtered_data = [data for data in all_data if len(data['extracted_data']['Fan Diameter']) == data['extracted_data']['Fan Number']]
                            best_img = max(filtered_data or all_data, key=lambda x: (x['num_instances'], sum(x['scores']) / len(x['scores'])))
                            extracted_data = best_img['extracted_data']
                            best_image_file_name = best_img['image_file_name']

                        # Initialize values
                        heatpipes_num = None
                        heatpipes_width = None
                        fans_num = None
                        fan_dimension = None
                        blade_count = None
                        ports_left = None
                        ports_right = None
                        ports_rear = None
                        ports_front = None
                        vc = "none"

                        if extracted_data:
                            heatpipes_num = max(int(extracted_data.get("Heat Pipe Number") or 0), heatpipes_num or 0)
                            heatpipes_width = max(float(extracted_data.get("Heat Pipe Width") or 0), heatpipes_width or 0)
                            fans_num = max(int(extracted_data.get("Fan Number") or 0), fans_num or 0)
                            fan_dimension = extracted_data.get("Fan Dimension") or fan_dimension
                            blade_count = extracted_data.get("Fan Blade Number") or blade_count
                            ports_left = str(extracted_data["Ports"]) if extracted_data["Side"] == "left" else ports_left
                            ports_right = str(extracted_data["Ports"]) if extracted_data["Side"] == "right" else ports_right
                            ports_rear = str(extracted_data["Ports"]) if extracted_data["Side"] == "rear" else ports_rear
                            ports_front = str(extracted_data["Ports"]) if extracted_data["Side"] == "front" else ports_front
                            vc = "possible" if heatpipes_num <= 0 and fans_num > 0 else "none"

                        # Directly update CSV after processing each row
                        update_row_in_csv([(heatpipes_num, heatpipes_width, fans_num, str(fan_dimension), str(blade_count), ports_left, ports_right, ports_rear, ports_front, vc, best_image_file_name, review_hash_id)], CSV_FILE_PATH)
                        logging.info(f"Successfully updated hash_id: {review_hash_id}, row_num = {row_num + 1}/{total_row_count}")
                        shutil.rmtree(image_directory)
                        logging.info(f"Image Directory '{image_directory}' has been deleted.")
            else:
                logging.info("No rows to update")

        except Exception as e:
            logging.error(f"Error occurred: {e}, Details: {traceback.format_exc()}")

        end_time = time.time()
        execution_time_seconds = end_time - start_time

        hours = int(execution_time_seconds // 3600)
        minutes = int((execution_time_seconds % 3600) // 60)
        seconds = int(execution_time_seconds % 60)

        logging.info("Script ended")
        logging.info(f"Total execution time: {hours} hours, {minutes} minutes, {seconds} seconds")