import wave
from os import listdir
from os.path import join
import os
import numpy as np
import sys
import cProfile
import math
import argparse


class AudioMatcher:
	def __init__(self, childFolder, parentPath):
		self.parent = wave.open(parentPath, "rb")
		self.parentFrameCount = self.parent.getnframes()
		self.maxValue = 2 ** (8 * self.parent.getsampwidth())
		print("initing parent data")
		self.parentData = [self.parent.readframes(1) for f in range(self.parentFrameCount)]
		#print(self.parentData)

		print("initing child data")
		self.children = [wave.open(join(childFolder, f), "rb") for f in listdir(childFolder) if os.path.isfile(join(childFolder, f))]
		self.childrenData = self.initChildData()
		#print(self.childrenData)

		self.diffMap = self.initDiffMap()

	def initChildData(self):
		allChildData = []
		for c in self.children:
			thisChildData = []
			for frame in range(self.parentFrameCount): #only going to make it as long as parent, so no need to read extra
				thisChildData.append(c.readframes(1))
			allChildData.append(thisChildData)

		return allChildData

	def initDiffMap(self):
		print("initing diff map")
		diffMap = {}
		print("parent frame count: " + str(self.parentFrameCount))
		for i in range(len(self.children)):
			child = self.children[i]
			childrenData = self.childrenData[i]

			diffMap[i] = np.zeros((self.parentFrameCount, 1), dtype=np.int16)

			for frameNum in range(self.parentFrameCount):
				if(frameNum % 100000 == 0):
					print(str(frameNum) + " / " + str(self.parentFrameCount) + " (" + str(frameNum / self.parentFrameCount * 100) + "%)")
				sample = self.parentData[frameNum]
				childSample = childrenData[frameNum]
				diffMap[i][frameNum] = self.distance(sample, childSample)

		print("initted diff map")
		return diffMap

	def makeCompares(self, outputFolder, start, stop, step=1, maxMin="max"):
			#print("starting " + str(i) + " of " + str(stop) + " (" + str(float(i-start)/float(stop-start)*100) + "%)")
		outputFileName = outputFolder + "/out_" + str(start) + "_" + str(stop) + "_ " + str(step) + ".wav"
		if maxMin == "max":
			self.maxCompare(start, stop, step, outputFileName)
		elif maxMin == "min":
			self.minCompare(start, stop, step, outputFileName)
		else:
			raise ValueError("Invalid argument for maxMin")


	def compare(self, start, stop, step, outputFileName, distancesArray, eligiblityFunction):
		with wave.open(outputFileName, "wb") as outputFile:
			outputFile.setnchannels(self.parent.getnchannels())
			outputFile.setsampwidth(self.parent.getsampwidth())
			outputFile.setframerate(self.parent.getframerate())
			outputFile.setnframes(self.parentFrameCount)

			close = 0
			total = 0

			#TODO loop per frame, then per child. That way we can write as we go, saving memory
			for frame in range(self.parentFrameCount):
				outputFrame = self.parentData[frame]

				for i in range(len(self.children)):
					child = self.children[i]
					childrenData = self.childrenData[i]
					childDiffMap = self.diffMap[i]

					distanceThreshold = int(frame * ((stop - start) / (self.parentFrameCount))) #TODO not sure how to do step
					if(frame % 10000 == 0):
						print(str(frame) + " / " + str(self.parentFrameCount) + " (" + str(frame / self.parentFrameCount * 100) + "%)" + ", distanceThreshold: " + str(distanceThreshold))
					childSample = childrenData[frame]
					dist = childDiffMap[frame]

					if eligiblityFunction(dist, distanceThreshold, distancesArray, frame):
						distancesArray[frame] = dist
						#close += 1
						outputFrame = childSample
					# total += 1

				outputFile.writeframesraw(outputFrame)
			# print("max of max: " + str(max(distancesArray.flatten('F').tolist())))
			# print("close: " + str(close) + ", total: " + str(total) + " percent: " + str(float(close)/float(total) * 100))

	def maxEligibilityFunction(self, distance, distanceThreshold, maxDistances, frame):
		return distance < distanceThreshold and distance > maxDistances[frame]

	def minEligibilityFunction(self, distance, distanceThreshold, minDistances, frame):
		return distance < distanceThreshold and distance < minDistances[frame]


	def maxCompare(self, start, stop, step, outputFileName):
		maxDistances = np.zeros((self.parentFrameCount, 1), dtype=np.int16)

		return self.compare(start, stop, step, outputFileName, maxDistances, self.maxEligibilityFunction)

	def minCompare(self, start, stop, step, outputFileName):
		minDistances = np.full((self.parentFrameCount, 1), 9999999, dtype=np.int16)
	
		return self.compare(start, stop, step, outputFileName, minDistances, self.minEligibilityFunction)
	

	def distance(self, sample1, sample2):
		sample1Hex = sample1.hex()
		sample2Hex = sample2.hex()
		sample1Int = int(sample1Hex, 16) if sample1Hex != "" else 0
		sample2Int = int(sample2Hex, 16) if sample2Hex != "" else 0
		if(sample1Int > sample2Int):
			return min(sample1Int - sample2Int, self.maxValue - (sample1Int - sample2Int - 1))
		else:
			return min(sample2Int - sample1Int, self.maxValue - (sample2Int - sample1Int - 1))


def main(start, stop, outputFolder, childFolder, parentPath, maxMin="max", step=1):
	# print("start" + str(start) + str(type(start)))
	# print("stop" + str(stop) + str(type(stop)))
	# print("outputFolder" + str(outputFolder) + str(type(outputFolder)))
	# print("childFolder" + str(childFolder) + str(type(childFolder)))
	# print("parentPath" + str(parentPath) + str(type(parentPath)))
	# print("maxMin" + str(maxMin) + str(type(maxMin)))
	# print("step" + str(step) + str(type(step)))
	
	runner = AudioMatcher(childFolder, parentPath)
	runner.makeCompares(outputFolder, start, stop, step=step, maxMin=maxMin)

if __name__ == '__main__':
	main(0, 65535, "./output/", "./moonlight_sonata/", "./Beethoven_Moonlight_sonata_sequenced.wav")