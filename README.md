# spine-xray-processor
## Graphical user interface for performing image pre-processing on radiographic images of various spinal features and saving them to use for segmentation
### Spinal column
#### Input:
- spinal posteroanterior radiograph

#### Pre-processing procedure:
- Crop sensitive info (remove top 100 rows)
- Get region of interest by looking for head/neck at the top of the radiograph (crop out 1000-pixel width image)
- Contrast limited adaptive histogram equalization on region of interest

### Vertebral body
#### Input:
- square image centered on the vertebral body (T1-L5, inclusive) with some margins at the sides and top/bottom

#### Pre-processing procedure:
- Histogram equalization

### Pedicles
#### Input:
- square image centered on the vertebral body (T4-L5, inclusive) with some margins at the sides and top/bottom

#### Pre-processing procedure:
- Adaptive histogram equalization
