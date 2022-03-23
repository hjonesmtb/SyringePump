import os
import pandas as pd
import matplotlib.pyplot as plt
import imageio

dfinit = pd.read_csv(r"C:\Users\mykal\OneDrive - UBC\Capstone\first_sqv_Dan2_Test_22-03-21_1600\csv\swv01.csv")
df28 = pd.read_csv(r"C:\Users\mykal\OneDrive - UBC\Capstone\first_sqv_Dan2_Test_22-03-21_1600\csv\swv28.csv")
for filename in os.listdir(r"C:\Users\mykal\OneDrive - UBC\Capstone\first_sqv_Dan2_Test_22-03-21_1600\csv"):
    df = pd.read_csv(r"C:\Users\mykal\OneDrive - UBC\Capstone\first_sqv_Dan2_Test_22-03-21_1600\csv\{}".format(filename))
    df.plot(x="Potential", y="Current", legend=None)
    plt.title("Allura Red Passing Through FLow Cell \n Squarewave Measurement #{}".format(filename[3:5]))
    plt.ylabel("Current (uA)")
    plt.xlabel("Potential (V)")
    plt.ylim(0.1,0.5)
    plt.savefig(r"C:\Users\mykal\OneDrive - UBC\Capstone\first_sqv_Dan2_Test_22-03-21_1600\plots\{}.png".format(filename[:-4]))
    plt.clf()
    df['subtracted'] = df['Current'] - dfinit['Current']
    df.plot(x="Potential", y="subtracted", legend=None)
    plt.title("Allura Red Passing Through FLow Cell \n Squarewave Measurement, Subtracted From Baseline #{}".format(filename[3:5]))
    plt.ylabel("Current (uA)")
    plt.xlabel("Potential (V)")
    plt.ylim(-0.5, 0.5)
    plt.savefig(r"C:\Users\mykal\OneDrive - UBC\Capstone\first_sqv_Dan2_Test_22-03-21_1600\plotssub\{}.png".format(filename[:-4]))
    plt.clf()

frames = []
# Build GIF
with imageio.get_writer(r"C:\Users\mykal\OneDrive - UBC\Capstone\first_sqv_Dan2_Test_22-03-21_1600\progression.gif", mode='I', duration=0.2) as writer:
    for filename in os.listdir(r"C:\Users\mykal\OneDrive - UBC\Capstone\first_sqv_Dan2_Test_22-03-21_1600\plots"):
        image = imageio.imread(r"C:\Users\mykal\OneDrive - UBC\Capstone\first_sqv_Dan2_Test_22-03-21_1600\plots\{}".format(filename))
        writer.append_data(image)

with imageio.get_writer(r"C:\Users\mykal\OneDrive - UBC\Capstone\first_sqv_Dan2_Test_22-03-21_1600\subtracted.gif", mode='I', duration=0.2) as writer2:
    for filename2 in os.listdir(r"C:\Users\mykal\OneDrive - UBC\Capstone\first_sqv_Dan2_Test_22-03-21_1600\plotssub"):
        image2 = imageio.imread(r"C:\Users\mykal\OneDrive - UBC\Capstone\first_sqv_Dan2_Test_22-03-21_1600\plotssub\{}".format(filename2))
        writer2.append_data(image2)
