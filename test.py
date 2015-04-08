import sys
import os
import subprocess as sub

commands { 'run':None,
          'clean':None,
          'stdout':None,
          "":None,
}


if __name__ == "__main__":
      if len(sys.argv) > 1:
           args = sys.argv[1:]
      
